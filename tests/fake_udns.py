import asyncio
from collections import namedtuple
from contextlib import contextmanager
from ipaddress import IPv4Address
from itertools import chain
import logging
import struct
from typing import Dict, List, Mapping, NamedTuple, Optional, Tuple, Union, cast
from unittest.mock import patch

from pyatv.core import mdns
from pyatv.support import dns

from tests.support import dns_utils

_LOGGER = logging.getLogger(__name__)


class FakeDnsService(NamedTuple):
    """Representation of fake DNS service."""

    name: str
    addresses: List[str]
    port: int
    properties: Mapping[str, str]
    model: Optional[str]


def mrp_service(
    service_name: str,
    atv_name: str,
    identifier: str,
    addresses: List[str] = ["127.0.0.1"],
    port: int = 49152,
    model: Optional[str] = None,
    version: str = "18M60",
) -> Tuple[str, FakeDnsService]:
    service = FakeDnsService(
        name=service_name,
        addresses=addresses,
        port=port,
        properties={
            "Name": atv_name.encode("utf-8"),
            "UniqueIdentifier": identifier.encode("utf-8"),
            "SystemBuildVersion": version.encode("utf-8"),
        },
        model=model,
    )
    return ("_mediaremotetv._tcp.local", service)


def airplay_service(
    atv_name: str,
    deviceid: str,
    addresses: List[str] = ["127.0.0.1"],
    port: int = 7000,
    model: Optional[str] = None,
) -> Tuple[str, FakeDnsService]:
    service = FakeDnsService(
        name=atv_name,
        addresses=addresses,
        port=port,
        properties={"deviceid": deviceid.encode("utf-8"), "features": b"0x1"},
        model=model,
    )
    return ("_airplay._tcp.local", service)


def homesharing_service(
    service_name: str,
    atv_name: str,
    hsgid: str,
    addresses: List[str] = ["127.0.0.1"],
    model: Optional[str] = None,
) -> Tuple[str, FakeDnsService]:
    service = FakeDnsService(
        name=service_name,
        addresses=addresses,
        port=3689,
        properties={"hG": hsgid.encode("utf-8"), "Name": atv_name.encode("utf-8")},
        model=model,
    )
    return ("_appletv-v2._tcp.local", service)


def device_service(
    service_name: str,
    atv_name: str,
    addresses: List[str] = ["127.0.0.1"],
    model: Optional[str] = None,
):
    service = FakeDnsService(
        name=service_name,
        addresses=addresses,
        port=3689,
        properties={"CtlN": atv_name.encode("utf-8")},
        model=model,
    )
    return ("_touch-able._tcp.local", service)


def companion_service(
    service_name: str,
    addresses: List[str] = ["127.0.0.1"],
    port: int = 0,
    model: Optional[str] = None,
) -> Tuple[str, FakeDnsService]:
    service = FakeDnsService(
        name=service_name,
        addresses=addresses,
        port=port,
        properties={"rpHA": "33efedd528a".encode("utf-8")},
        model=model,
    )
    return ("_companion-link._tcp.local", service)


def raop_service(
    name: str,
    identifier: str,
    addresses: List[str] = ["127.0.0.1"],
    port: int = 0,
    model: Optional[str] = None,
) -> Tuple[str, FakeDnsService]:
    service = FakeDnsService(
        name=identifier + "@" + name,
        addresses=addresses,
        port=port,
        properties={},
        model=model,
    )
    return ("_raop._tcp.local", service)


def hscp_service(
    name: str,
    identifier: str,
    hsgid: str,
    addresses: List[str] = ["127.0.0.1"],
    port: int = 0,
    model: Optional[str] = None,
) -> Tuple[str, FakeDnsService]:
    service = FakeDnsService(
        name="HSCP Name",
        addresses=addresses,
        port=port,
        properties={
            "Machine Name": name.encode("utf-8"),
            "Machine ID": identifier.encode("utf-8"),
            "hG": hsgid.encode("utf-8"),
        },
        model=model,
    )
    return ("_hscp._tcp.local", service)


def _lookup_service(
    question: dns.DnsQuestion,
    services: Dict[str, FakeDnsService],
) -> Union[Tuple[None, None], Tuple[FakeDnsService, str]]:
    """Given a DNS query and the registered fake services, find a matching service."""
    if question.qname.startswith("_"):
        service = services.get(question.qname)
        if service is not None:
            return service, service.name + "." + question.qname
        else:
            return None, None

    service_name, _, service_type = question.qname.partition(".")
    for name, service in services.items():
        if service_type == name and service_name == service.name:
            return service, question.qname

    return None, None


def create_response(
    request: bytes,
    services: Dict[str, FakeDnsService],
    ip_filter: Optional[str] = None,
    sleep_proxy: bool = False,
):
    msg = dns.DnsMessage().unpack(request)

    resp = dns.DnsMessage()
    resp.flags = 0x0840
    resp.questions = msg.questions

    for question in resp.questions:
        service, full_name = _lookup_service(question, services)
        if service is None or (ip_filter and ip_filter not in service.addresses):
            continue

        # For typing purposes, because service is not None, then full_name is not None
        # either.
        full_name = cast(str, full_name)

        # Add answer
        if full_name:
            resp.answers.append(dns_utils.answer(question.qname, full_name))

            # If acting as sleep proxy, just return a PTR
            if sleep_proxy and question.qname.startswith("_"):
                continue

        # Add service (SRV) resource
        if service.port:
            local_name = dns.qname_encode(service.name + ".local")
            rd = struct.pack(">3H", 0, 0, service.port) + local_name
            resp.resources.append(dns_utils.resource(full_name, dns.QueryType.SRV, rd))

        # Add IP address(es)
        for address in service.addresses:
            ipaddr = IPv4Address(address).packed
            resp.resources.append(
                dns_utils.resource(service.name + ".local", dns.QueryType.A, ipaddr)
            )

        # Add properties
        if service.properties:
            rd = dns_utils.properties(service.properties)
            resp.resources.append(dns_utils.resource(full_name, dns.QueryType.TXT, rd))

        # Add model if present
        if service.model:
            rd = dns_utils.properties({"model": service.model.encode("utf-8")})
            resp.resources.append(
                dns_utils.resource(
                    service.name + "._device-info._tcp.local", dns.QueryType.TXT, rd
                )
            )

    return resp


class FakeUdns(asyncio.Protocol):
    def __init__(self, loop, services=None):
        self.loop = loop
        self.server = None
        self.services: Dict[str, FakeDnsService] = services or {}
        self.skip_count: int = 0  # Ignore sending respone to this many requests
        self.ip_filter = None
        self.sleep_proxy: bool = False
        self.request_count: int = 0

    async def start(self):
        self.server, _ = await self.loop.create_datagram_endpoint(
            lambda: self, local_addr=("127.0.0.1", None)
        )
        _LOGGER.debug("Starting fake UDNS server at port %d", self.port)

    def close(self):
        self.server.close()

    def add_service(self, service: Tuple[str, FakeDnsService]):
        self.services[service[0]] = service[1]

    @property
    def port(self):
        return self.server.get_extra_info("socket").getsockname()[1]

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data: bytes, addr):
        msg = dns.DnsMessage().unpack(data)
        _LOGGER.debug("Received DNS request %s: %s", addr, msg)

        if self.skip_count > 0:
            _LOGGER.debug("Not sending DNS response (%d)", self.skip_count)
            self.skip_count -= 1
            return

        resp = create_response(data, self.services, self.ip_filter, self.sleep_proxy)
        self.transport.sendto(resp.pack(), addr)
        self.request_count += 1


@contextmanager
def stub_multicast(udns_server, loop):
    patcher = patch("pyatv.core.mdns.multicast")

    async def _multicast(loop, services, **kwargs):
        # Flatten list of lists of addresses: [["1.2.3.4"], ["2.2.2.2"]] -> ["1.2.3.4", "2.2.2.2"]
        hosts = set(
            chain(*[service.addresses for service in udns_server.services.values()])
        )
        devices = []
        sleep_proxy = udns_server.sleep_proxy
        udns_server.sleep_proxy = False
        for host in hosts:
            udns_server.ip_filter = host
            response = await mdns.unicast(
                loop, "127.0.0.1", services, port=udns_server.port
            )
            devices.append(
                mdns.Response(response.services, sleep_proxy, response.model)
            )
        return devices

    try:
        patched_fn = patcher.start()
        patched_fn.side_effect = _multicast
        yield patched_fn
    except Exception:
        _LOGGER.exception("multicast scan failed")
    finally:
        patcher.stop()
