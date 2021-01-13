"""Minimalistic DNS-SD implementation."""
import asyncio
import logging
import math
import socket
import weakref
from ipaddress import IPv4Address, ip_address
import typing

from zeroconf import Zeroconf, ServiceInfo

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


def _decode_properties(
    properties: typing.Mapping[str, bytes],
) -> CaseInsensitiveDict[str]:
    def _decode(value: bytes):
        try:
            # Remove non-breaking-spaces (0xA2A0, 0x00A0) before decoding
            return (
                value.replace(b"\xC2\xA0", b" ")
                .replace(b"\x00\xA0", b" ")
                .decode("utf-8")
            )
        except Exception:  # pylint: disable=broad-except
            return str(value)

    return CaseInsensitiveDict({k: _decode(v) for k, v in properties.items()})


def create_request(
    services: typing.List[str], qtype: QueryType = QueryType.PTR
) -> bytes:
    """Create a new DnsMessage requesting specified services."""
    msg = DnsMessage(0x35FF)
    msg.questions += [DnsQuestion(s, qtype, 0x8001) for s in services]
    return msg.pack()


def _get_model(services: typing.List[Service]) -> typing.Optional[str]:
    for service in services:
        if service.type == DEVICE_INFO_SERVICE:
            return service.properties.get("model")
    return None


def parse_services(message: DnsMessage) -> typing.List[Service]:
    """Parse DNS response into Service objects."""
    table: typing.Dict[str, typing.Dict[int, DnsResource]] = {}
    ptrs: typing.Dict[str, str] = {}  # qname -> real name
    results: typing.Dict[str, Service] = {}

    # Create a global table with all records
    for record in message.answers + message.resources:
        if record.qtype == QueryType.PTR and record.qname.startswith("_"):
            ptrs[record.qname] = record.rd
        else:
            table.setdefault(record.qname, {})[record.qtype] = record

    # Build services
    for service, device in table.items():
        try:
            service_name = ServiceInstanceName.split_name(service)
        except ValueError:
            continue

        port = (QueryType.SRV in device and device[QueryType.SRV].rd["port"]) or 0
        target = (
            QueryType.SRV in device and device[QueryType.SRV].rd["target"]
        ) or None
        properties = (QueryType.TXT in device and device[QueryType.TXT].rd) or {}

        target_record = table.get(typing.cast(str, target), {}).get(QueryType.A)
        address = IPv4Address(target_record.rd) if target_record else None

        results[service] = Service(
            service_name.ptr_name,
            typing.cast(str, service_name.instance),
            address,
            port,
            _decode_properties(properties),
        )

    # If there are PTRs to unknown services, create placeholders
    for qname, real_name in ptrs.items():
        if real_name not in results:
            results[real_name] = Service(qname, real_name.split(".")[0], None, 0, {})

    return list(results.values())


class UnicastDnsSdClientProtocol(asyncio.Protocol):
    """Protocol to make unicast requests."""

    def __init__(self, services: typing.List[str], host: str, timeout: int):
        """Initialize a new UnicastDnsSdClientProtocol."""
        self.message = create_request(services)
        self.host = host
        self.timeout = timeout
        self.transport = None
        self.semaphore: asyncio.Semaphore = asyncio.Semaphore(value=0)
        self.result: DnsMessage = DnsMessage()
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
        services = parse_services(self.result)
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
            log_binary(
                _LOGGER,
                "Sending DNS request to " + self.host,
                level=TRAFFIC_LEVEL,
                Data=self.message,
            )

            self.transport.sendto(self.message)
            await asyncio.sleep(1)

    def datagram_received(self, data: bytes, _) -> None:
        """DNS response packet received."""
        log_binary(
            _LOGGER,
            "Received DNS response from " + self.host,
            level=TRAFFIC_LEVEL,
            Data=data,
        )

        self.result = DnsMessage().unpack(data)
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


class MulticastDnsSdClientProtocol:
    """Protocol to make multicast requests."""

    def __init__(
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
        self.message = create_request(services)
        self.address = address
        self.port = port
        self.end_condition = end_condition or (lambda _: False)
        self.semaphore: asyncio.Semaphore = asyncio.Semaphore(value=0)
        self.responses: typing.Dict[IPv4Address, Response] = {}
        self._unicasts: typing.Dict[IPv4Address, bytes] = {}
        self._task: typing.Optional[asyncio.Future] = None
        self._receivers: typing.List[asyncio.BaseProtocol] = []

    async def add_socket(self, sock: socket.socket):
        """Add a new multicast socket."""
        _, protocol = await self.loop.create_datagram_endpoint(
            lambda: ReceiveDelegate(self),
            sock=sock,
        )

        self._receivers.append(protocol)

    async def get_response(self, timeout: int) -> typing.Dict[IPv4Address, Response]:
        """Get respoonse with a maximum timeout."""
        # Semaphore used here as a quick-bailout when testing
        try:
            self._task = asyncio.ensure_future(self._resend_loop(timeout))
            await asyncio.wait_for(self.semaphore.acquire(), timeout=timeout)
        except asyncio.TimeoutError:
            pass
        finally:
            self.close()

        return self.responses

    async def _resend_loop(self, timeout):
        for _ in range(math.ceil(timeout)):
            log_binary(
                _LOGGER,
                f"Sending multicast DNS request to {self.address}:{self.port}",
                level=TRAFFIC_LEVEL,
                Data=self.message,
            )

            self._sendto(self.message, (self.address, self.port))

            # Send unicast requests if devices are sleeping
            for address, message in self._unicasts.items():
                log_binary(
                    _LOGGER,
                    f"Sending unicast DNS request to {address}:{self.port}",
                    level=TRAFFIC_LEVEL,
                    Data=message,
                )
                self._sendto(message, (address, self.port))

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

        # Suppress decode errors for now (but still log)
        try:
            services = parse_services(DnsMessage().unpack(data))
        except UnicodeDecodeError:
            log_binary(_LOGGER, "Failed to decode message", Msg=data)
            return

        # Ignore responses from other services
        for service in services:
            if (
                service.type not in self.services
                and service.type != DEVICE_INFO_SERVICE
            ):
                return

        is_sleep_proxy = all(service.port == 0 for service in services)
        if is_sleep_proxy:
            self._unicasts[addr[0]] = create_request(
                [service.name + "." + service.type for service in services],
                qtype=QueryType.ANY,
            )
        else:
            response = Response(
                services=services,
                deep_sleep=(addr[0] in self._unicasts),
                model=_get_model(services),
            )

            if self.end_condition(response):
                # Matches end condition: replace everything found so far and abort
                self.responses = {IPv4Address(addr[0]): response}
                self.semaphore.release()
                self.close()
            else:
                self.responses[IPv4Address(addr[0])] = response

    def error_received(self, exc) -> None:
        """Error received during communication."""
        _LOGGER.debug("Error during MDNS lookup: %s", exc)

    def close(self):
        """Close resources used by this instance."""
        for receiver in self._receivers:
            receiver.close()

        if self._task:
            self._task.cancel()
            self._task = None


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


async def multicast(
    loop: asyncio.AbstractEventLoop,
    services: typing.List[str],
    address: str = "224.0.0.251",
    port: int = 5353,
    timeout: int = 4,
    end_condition: typing.Optional[typing.Callable[[Response], bool]] = None,
) -> typing.Dict[IPv4Address, Response]:
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
            _LOGGER.exception(f"failed to add listener for {addr}")

    return await typing.cast(MulticastDnsSdClientProtocol, protocol).get_response(
        timeout
    )


async def publish(loop: asyncio.AbstractEventLoop, service: Service, zconf: Zeroconf):
    """Publish an MDNS service on the network."""
    if service.address is None:
        raise Exception(f"no address for {service.name}.{service.type}")
    zsrv = ServiceInfo(
        f"{service.type}.",
        f"{service.name}.{service.type}.",
        addresses=[service.address.packed],
        port=service.port,
        properties=service.properties,
    )

    _LOGGER.debug("Publishing zeroconf service: %s", zsrv)
    await loop.run_in_executor(None, zconf.register_service, zsrv)

    async def _unregister():
        _LOGGER.debug("Unregistering service %s", zsrv)
        await loop.run_in_executor(None, zconf.unregister_service, zsrv)

    return _unregister
