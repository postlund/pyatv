"""Minimalistic DNS-SD implementation."""

import asyncio
from ipaddress import IPv4Address, ip_address
import logging
import math
import socket
from types import SimpleNamespace
import typing
import weakref

from zeroconf import ServiceInfo, Zeroconf

from pyatv import exceptions
from pyatv.support import log_binary, net
from pyatv.support.collections import CaseInsensitiveDict
from pyatv.support.dns import (
    DnsMessage,
    DnsQuestion,
    DnsResource,
    QueryType,
    ServiceInstanceName,
)

_LOGGER = logging.getLogger(__name__)

# Number of services to include in each request
SERVICES_PER_MSG = 3

SLEEP_PROXY_SERVICE = "_sleep-proxy._udp.local"

# This module produces a lot of debug output, use a dedicated log level.
# Maybe move this to top-level support later?
TRAFFIC_LEVEL = logging.DEBUG - 5
setattr(logging, "TRAFFIC", TRAFFIC_LEVEL)
logging.addLevelName(TRAFFIC_LEVEL, "Traffic")


class Service(typing.NamedTuple):
    """Represent an MDNS service."""

    type: str
    name: str
    address: typing.Optional[IPv4Address]
    port: int
    properties: typing.Mapping[str, str]


class Response(typing.NamedTuple):
    """Represent response to an MDNS request."""

    services: typing.List[Service]
    deep_sleep: bool
    model: typing.Optional[str]  # Comes from _device-info._tcp.local


DEVICE_INFO_SERVICE = "_device-info._tcp.local"


def decode_value(value: bytes):
    """Decode a bytes value and convert non-breaking-spaces.

    (0xA2A0, 0x00A0) are converted to spaces before decoding.
    """
    try:
        return (
            value.replace(b"\xc2\xa0", b" ").replace(b"\x00\xa0", b" ").decode("utf-8")
        )
    except Exception:  # pylint: disable=broad-except
        return str(value)


def _decode_properties(
    properties: typing.Mapping[str, bytes],
) -> CaseInsensitiveDict[str]:
    return CaseInsensitiveDict({k: decode_value(v) for k, v in properties.items()})


def create_service_queries(
    services: typing.List[str], qtype: QueryType
) -> typing.List[bytes]:
    """Create service request messages."""
    queries: typing.List[bytes] = []
    for i in range(math.ceil(len(services) / SERVICES_PER_MSG)):
        service_chunk = services[i * SERVICES_PER_MSG : i * SERVICES_PER_MSG + 4]

        msg = DnsMessage(0x35FF)
        msg.questions += [DnsQuestion(s, qtype, 0x8001) for s in service_chunk]
        msg.questions += [DnsQuestion(SLEEP_PROXY_SERVICE, qtype, 0x8001)]

        queries.append(msg.pack())
    return queries


def _get_model(services: typing.List[Service]) -> typing.Optional[str]:
    for service in services:
        if service.type == DEVICE_INFO_SERVICE:
            return service.properties.get("model")
    return None


def _first_rd(qtype: QueryType, entries: typing.Dict[int, typing.List[DnsResource]]):
    return entries[qtype][0].rd if qtype in entries else None


class ServiceParser:
    """Parse zeroconf services from records in DNS messages."""

    def __init__(self) -> None:
        """Initialize a new ServiceParser instance."""
        self.table: typing.Dict[str, typing.Dict[int, typing.List[DnsResource]]] = {}
        self.ptrs: typing.Dict[str, str] = {}  # qname -> real name
        self._cache: typing.Optional[typing.List[Service]] = None

    def add_message(self, message: DnsMessage) -> "ServiceParser":
        """Add message to with records to parse."""
        self._cache = None

        for record in message.answers + message.resources:
            if record.qtype == QueryType.PTR and record.qname.startswith("_"):
                self.ptrs[record.qname] = record.rd
            else:
                entry = self.table.setdefault(record.qname, {})
                if record.qtype not in entry:
                    entry[record.qtype] = []

                if record not in entry[record.qtype]:
                    entry[record.qtype].append(record)
        return self

    def parse(self) -> typing.List[Service]:
        """Parse records and return services."""
        if self._cache:
            return self._cache

        results: typing.Dict[str, Service] = {}

        # Build services
        for service, device in self.table.items():
            try:
                service_name = ServiceInstanceName.split_name(service)
            except ValueError:
                continue

            srv_rd = _first_rd(QueryType.SRV, device)
            target = srv_rd["target"] if srv_rd else None

            target_records = self.table.get(typing.cast(str, target), {}).get(
                QueryType.A, []
            )
            address = None

            # Pick one address that is not link-local
            for addr in [IPv4Address(record.rd) for record in target_records]:
                if not addr.is_link_local:
                    address = addr
                    break

            results[service] = Service(
                service_name.ptr_name,
                typing.cast(str, service_name.instance),
                address,
                srv_rd["port"] if srv_rd else 0,
                _decode_properties(_first_rd(QueryType.TXT, device) or {}),
            )

        # If there are PTRs to unknown services, create placeholders
        for qname, real_name in self.ptrs.items():
            if real_name not in results:
                results[real_name] = Service(
                    qname, real_name.split(".")[0], None, 0, {}
                )
        self._cache = list(results.values())
        return self._cache


class QueryResponse(SimpleNamespace):
    """Hold DNS query response records."""

    count: int
    deep_sleep: bool
    parser: ServiceParser


class UnicastDnsSdClientProtocol(asyncio.Protocol):
    """Protocol to make unicast requests."""

    def __init__(self, services: typing.List[str], host: str, timeout: int):
        """Initialize a new UnicastDnsSdClientProtocol."""
        self.queries = create_service_queries(services, QueryType.PTR)
        self.host = host
        self.timeout = timeout
        self.transport = None
        self.parser: ServiceParser = ServiceParser()
        self.semaphore: asyncio.Semaphore = asyncio.Semaphore(value=0)
        self.received_responses: int = 0
        self._task: typing.Optional[asyncio.Future] = None

    async def get_response(self) -> Response:
        """Get respoonse with a maximum timeout."""
        try:
            await asyncio.wait_for(
                self.semaphore.acquire(),
                timeout=self.timeout,
            )
        finally:
            self._finished()
        if self._task:
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        services = self.parser.parse()
        return Response(
            services=services,
            deep_sleep=False,
            model=_get_model(services),
        )

    def connection_made(self, transport) -> None:
        """Establish connection to host."""
        self.transport = transport
        self._task = asyncio.ensure_future(self._resend_loop())

    async def _resend_loop(self):
        for _ in range(math.ceil(self.timeout)):
            for query in self.queries:
                log_binary(
                    _LOGGER,
                    "Sending DNS request to " + self.host,
                    level=TRAFFIC_LEVEL,
                    Data=query,
                )

                self.transport.sendto(query)
            await asyncio.sleep(1)

    def datagram_received(self, data: bytes, _) -> None:
        """DNS response packet received."""
        log_binary(
            _LOGGER,
            "Received DNS response from " + self.host,
            level=TRAFFIC_LEVEL,
            Data=data,
            Index=self.received_responses + 1,
            Total=len(self.queries),
        )

        self.parser.add_message(DnsMessage().unpack(data))
        self.received_responses += 1

        if self.received_responses == len(self.queries):
            self._finished()
            if self.transport:
                self.transport.close()

    def error_received(self, exc) -> None:
        """Error received during communication."""
        _LOGGER.debug("Error during DNS lookup for %s: %s", self.host, exc)
        self._finished()

    def connection_lost(self, exc) -> None:
        """Lose connection to host."""
        self._finished()

    def _finished(self) -> None:
        self.semaphore.release()
        if self._task:
            self._task.cancel()


class ReceiveDelegate(asyncio.Protocol):
    """Delegate incoming data to another object."""

    def __init__(self, delegate) -> None:
        """Initialize a new ReceiveDelegate."""
        self.delegate = weakref.ref(delegate)
        self.transport = None
        self.is_loopback = False

    def sendto(self, message, target):
        """Send message to a target."""
        if not self.is_loopback:
            self.transport.sendto(message, target)

    def close(self):
        """Close underlying socket."""
        if self.transport:
            self.transport.close()

    def connection_made(self, transport) -> None:
        """Establish connection to host."""
        self.transport = transport

        # Determine if this is a loopback socket (don't send to those)
        sock = transport.get_extra_info("socket")
        address, _ = sock.getsockname()
        self.is_loopback = ip_address(address).is_loopback

    def datagram_received(self, data, addr) -> None:
        """Receive data from remote host."""
        delegate = self.delegate()
        if delegate is not None:
            try:
                delegate.datagram_received(data, addr)
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("exception during data handling")

    def error_received(self, exc) -> None:
        """Error during reception."""
        delegate = self.delegate()
        if delegate is not None:
            try:
                delegate.error_received(exc)
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("connection error")

    def __str__(self):
        """Return string representation of object."""
        return str(self.transport.get_extra_info("socket"))


class MulticastDnsSdClientProtocol:  # pylint: disable=too-many-instance-attributes
    """Protocol to make multicast requests."""

    def __init__(  # pylint: disable=too-many-arguments
        self,
        loop: asyncio.AbstractEventLoop,
        services: typing.List[str],
        address: str,
        port: int,
        end_condition: typing.Optional[typing.Callable[[Response], bool]],
    ) -> None:
        """Initialize a new MulticastDnsSdClientProtocol."""
        self.loop = loop
        self.services = services
        self.queries = create_service_queries(services, QueryType.PTR)
        self.query_responses: typing.Dict[str, QueryResponse] = {}
        self.address = address
        self.port = port
        self.end_condition = end_condition or (lambda _: False)
        self.semaphore: asyncio.Semaphore = asyncio.Semaphore(value=0)
        self.parser = ServiceParser()
        self._unicasts: typing.Dict[IPv4Address, typing.List[bytes]] = {}
        self._task: typing.Optional[asyncio.Future] = None
        self._receivers: typing.List[asyncio.BaseProtocol] = []

    async def add_socket(self, sock: socket.socket):
        """Add a new multicast socket."""
        _, protocol = await self.loop.create_datagram_endpoint(
            lambda: ReceiveDelegate(self),
            sock=sock,
        )

        self._receivers.append(protocol)

    async def get_response(self, timeout: int) -> typing.List[Response]:
        """Get respoonse with a maximum timeout."""
        # Semaphore used here as a quick-bailout when testing
        try:
            self._task = asyncio.ensure_future(self._resend_loop(timeout))
            await asyncio.wait_for(self.semaphore.acquire(), timeout=timeout)
        except asyncio.TimeoutError:
            pass
        finally:
            self.close()
            if self._task:
                try:
                    await self._task
                except asyncio.CancelledError:
                    pass
                self._task = None

        def _to_response(query_response: QueryResponse):
            services = query_response.parser.parse()
            return Response(
                services=services,
                deep_sleep=query_response.deep_sleep,
                model=_get_model(services),
            )

        return [_to_response(response) for response in self.query_responses.values()]

    async def _resend_loop(self, timeout):
        for _ in range(math.ceil(timeout)):
            for query in self.queries:
                log_binary(
                    _LOGGER,
                    f"Sending multicast DNS request to {self.address}:{self.port}",
                    level=TRAFFIC_LEVEL,
                    Data=query,
                )

                self._sendto(query, (self.address, self.port))

            # Send unicast requests if devices are sleeping
            for address, queries in self._unicasts.items():
                for query in queries:
                    log_binary(
                        _LOGGER,
                        f"Sending unicast DNS request to {address}:{self.port}",
                        level=TRAFFIC_LEVEL,
                        Data=query,
                    )
                    self._sendto(query, (address, self.port))

            await asyncio.sleep(1)

    def _sendto(self, message, target):
        for receiver in self._receivers:
            try:
                receiver.sendto(message, target)
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("fail to send to %r", receiver)

    def datagram_received(self, data, addr) -> None:
        """DNS response packet received."""
        log_binary(
            _LOGGER,
            f"Received DNS response from {addr}",
            level=TRAFFIC_LEVEL,
            Data=data,
        )

        query_resp = self.query_responses.setdefault(
            addr[0], QueryResponse(count=0, deep_sleep=False, parser=ServiceParser())
        )

        # Suppress decode errors for now (but still log)
        try:
            decoded_msg = DnsMessage().unpack(data)

            parser = ServiceParser()
            services = parser.add_message(decoded_msg).parse()
        except UnicodeDecodeError:
            log_binary(_LOGGER, "Failed to decode message", Msg=data)
            return

        if not services:
            return

        # Ignore responses from other services
        for service in services:
            if not (
                service.type in self.services
                or service.type in [DEVICE_INFO_SERVICE, SLEEP_PROXY_SERVICE]
            ):
                return

        is_sleep_proxy = all(service.port == 0 for service in services)
        query_resp.count += 1
        query_resp.deep_sleep |= is_sleep_proxy
        query_resp.parser.add_message(decoded_msg)

        if is_sleep_proxy:
            self._unicasts[addr[0]] = create_service_queries(
                [service.name + "." + service.type for service in services],
                QueryType.ANY,
            )
        elif query_resp.count >= len(self.queries):
            response = Response(
                services=query_resp.parser.parse(),
                deep_sleep=query_resp.deep_sleep,
                model=_get_model(query_resp.parser.parse()),
            )

            if self.end_condition(response):
                # Matches end condition: replace everything found so far and abort
                self.query_responses = {addr[0]: self.query_responses[addr[0]]}
                self.semaphore.release()
                self.close()

    @staticmethod
    def error_received(exc) -> None:
        """Error received during communication."""
        _LOGGER.debug("Error during MDNS lookup: %s", exc)

    def close(self):
        """Close resources used by this instance."""
        for receiver in self._receivers:
            receiver.close()
        if self._task:
            self._task.cancel()


async def unicast(
    loop: asyncio.AbstractEventLoop,
    address: str,
    services: typing.List[str],
    port: int = 5353,
    timeout: int = 4,
) -> Response:
    """Send request for services to a host."""
    transport, protocol = await loop.create_datagram_endpoint(
        lambda: UnicastDnsSdClientProtocol(services, address, timeout),
        remote_addr=(address, port),
    )

    try:
        return await typing.cast(UnicastDnsSdClientProtocol, protocol).get_response()
    finally:
        transport.close()


async def multicast(  # pylint: disable=too-many-arguments
    loop: asyncio.AbstractEventLoop,
    services: typing.List[str],
    address: str = "224.0.0.251",
    port: int = 5353,
    timeout: int = 4,
    end_condition: typing.Optional[typing.Callable[[Response], bool]] = None,
) -> typing.List[Response]:
    """Send multicast request for services."""
    protocol = MulticastDnsSdClientProtocol(
        loop, services, address, port, end_condition
    )

    # Socket listening on 5353 from anywhere
    await protocol.add_socket(net.mcast_socket(None, 5353))

    # One socket per local IP address
    for addr in net.get_private_addresses():
        try:
            await protocol.add_socket(net.mcast_socket(str(addr)))
        except Exception:  # pylint: disable=broad-except
            _LOGGER.debug("Failed to add listener for %s (ignoring)", addr)

    return await typing.cast(MulticastDnsSdClientProtocol, protocol).get_response(
        timeout
    )


async def publish(loop: asyncio.AbstractEventLoop, service: Service, zconf: Zeroconf):
    """Publish an MDNS service on the network."""
    if service.address is None:
        raise exceptions.InvalidConfigError(
            f"no address for {service.name}.{service.type}"
        )
    zsrv = ServiceInfo(
        f"{service.type}.",
        f"{service.name}.{service.type}.",
        addresses=[service.address.packed],
        port=service.port,
        properties=dict(service.properties),
    )

    _LOGGER.debug("Publishing zeroconf service: %s", zsrv)
    await loop.run_in_executor(None, zconf.register_service, zsrv)

    async def _unregister():
        _LOGGER.debug("Unregistering service %s", zsrv)
        await loop.run_in_executor(None, zconf.unregister_service, zsrv)

    return _unregister
