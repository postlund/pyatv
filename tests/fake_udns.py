import asyncio
import logging
import struct
from unittest.mock import patch
from contextlib import contextmanager
from ipaddress import IPv4Address
from collections import namedtuple

from pyatv.support import udns

from tests.support import dns_utils


_LOGGER = logging.getLogger(__name__)

FakeDnsService = namedtuple("FakeDnsService", "name address port properties")


def mrp_service(service_name, atv_name, identifier, address="127.0.0.1", port=49152):
    service = FakeDnsService(
        name=service_name,
        address=address,
        port=port,
        properties={"Name": atv_name, "UniqueIdentifier": identifier},
    )
    return ("_mediaremotetv._tcp.local", service)


def airplay_service(atv_name, deviceid, address="127.0.0.1", port=7000):
    service = FakeDnsService(
        name=atv_name, address=address, port=port, properties={"deviceid": deviceid}
    )
    return ("_airplay._tcp.local", service)


def homesharing_service(service_name, atv_name, hsgid, address="127.0.0.1"):
    service = FakeDnsService(
        name=service_name,
        address=address,
        port=3689,
        properties={"hG": hsgid, "Name": atv_name},
    )
    return ("_appletv-v2._tcp.local", service)


def device_service(service_name, atv_name, address="127.0.0.1"):
    service = FakeDnsService(
        name=service_name, address=address, port=3689, properties={"CtlN": atv_name}
    )
    return ("_touch-able._tcp.local", service)


class FakeUdns(asyncio.Protocol):
    def __init__(self, loop, services=None):
        self.loop = loop
        self.server = None
        self.services = services or {}
        self.skip_count = 0  # Ignore sending respone to this many requests
        self.ip_filter = None

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

    @property
    def request_count(self):
        return self._recv_count

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        msg = udns.DnsMessage().unpack(data)
        _LOGGER.debug("Received DNS request %s: %s", addr, msg)

        if self.skip_count > 0:
            _LOGGER.debug("Not sending DNS response (%d)", self.skip_count)
            self.skip_count -= 1
            return

        resp = udns.DnsMessage()
        resp.flags = 0x0840
        resp.questions = msg.questions

        for question in resp.questions:
            service = self.services.get(question.qname)
            if service is None or (
                self.ip_filter and service.address != self.ip_filter
            ):
                continue

            # Add answer
            full_name = service.name + "." + question.qname
            resp.answers.append(dns_utils.answer(question.qname, full_name))

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

        self.transport.sendto(resp.pack(), addr)


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
