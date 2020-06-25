import asyncio
import logging
import struct
from unittest.mock import patch
from contextlib import contextmanager
from ipaddress import IPv4Address
from collections import namedtuple
from typing import List, Dict, Optional, Tuple

from pyatv.support import udns

from tests.support import dns_utils


_LOGGER = logging.getLogger(__name__)

FakeDnsService = namedtuple("FakeDnsService", "name address port properties")


def mrp_service(service_name, atv_name, identifier, address="127.0.0.1", port=49152):
    service = FakeDnsService(
        name=service_name,
        address=address,
        port=port,
        properties={
            b"Name": atv_name.encode("utf-8"),
            b"UniqueIdentifier": identifier.encode("utf-8"),
        },
    )
    return ("_mediaremotetv._tcp.local", service)


def airplay_service(atv_name, deviceid, address="127.0.0.1", port=7000):
    service = FakeDnsService(
        name=atv_name,
        address=address,
        port=port,
        properties={b"deviceid": deviceid.encode("utf-8")},
    )
    return ("_airplay._tcp.local", service)


def homesharing_service(service_name, atv_name, hsgid, address="127.0.0.1"):
    service = FakeDnsService(
        name=service_name,
        address=address,
        port=3689,
        properties={b"hG": hsgid.encode("utf-8"), b"Name": atv_name.encode("utf-8")},
    )
    return ("_appletv-v2._tcp.local", service)


def device_service(service_name, atv_name, address="127.0.0.1"):
    service = FakeDnsService(
        name=service_name,
        address=address,
        port=3689,
        properties={b"CtlN": atv_name.encode("utf-8")},
    )
    return ("_touch-able._tcp.local", service)


def _lookup_service(
    question: udns.DnsQuestion, services: Dict[str, FakeDnsService]
) -> Tuple[Optional[FakeDnsService], Optional[str]]:
    if question.qname.startswith("_"):
        service = services.get(question.qname)
        return service, service.name + "." + question.qname if service else None

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
    msg = udns.DnsMessage().unpack(request)

    resp = udns.DnsMessage()
    resp.flags = 0x0840
    resp.questions = msg.questions

    for question in resp.questions:
        service, full_name = _lookup_service(question, services)
        if service is None or (ip_filter and service.address != ip_filter):
            continue

        # Add answer
        if full_name:
            resp.answers.append(dns_utils.answer(question.qname, full_name))

            # If acting as sleep proxy, just return a PTR
            if sleep_proxy and question.qname.startswith("_"):
                continue

        # Add service (SRV) resource
        if service.port:
            local_name = udns.qname_encode(service.name + ".local")
            rd = struct.pack(">3H", 0, 0, service.port) + local_name
            resp.resources.append(dns_utils.resource(full_name, udns.QTYPE_SRV, rd))

        # Add IP address
        if service.address:
            ipaddr = IPv4Address(service.address).packed
            resp.resources.append(
                dns_utils.resource(service.name + ".local", udns.QTYPE_A, ipaddr)
            )

        # Add properties
        if service.properties:
            rd = dns_utils.properties(service.properties)
            resp.resources.append(dns_utils.resource(full_name, udns.QTYPE_TXT, rd))

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
        _LOGGER.debug("Starting fake UDNS server")
        self.server, _ = await self.loop.create_datagram_endpoint(
            lambda: self, local_addr=("127.0.0.1", None)
        )

    def close(self):
        self.server.close()

    def add_service(self, service):
        self.services[service[0]] = service[1]

    @property
    def port(self):
        return self.server.get_extra_info("socket").getsockname()[1]

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data: bytes, addr):
        msg = udns.DnsMessage().unpack(data)
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
    patcher = patch("pyatv.support.udns.multicast")

    async def _multicast(loop, services, **kwargs):
        hosts = set(service.address for service in udns_server.services.values())
        devices = {}
        for host in hosts:
            udns_server.ip_filter = host
            devices[IPv4Address(host)] = await udns.unicast(
                loop, "127.0.0.1", services, port=udns_server.port
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
