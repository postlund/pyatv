import asyncio
import logging
import struct
from unittest.mock import patch
from contextlib import contextmanager
from ipaddress import IPv4Address
from collections import namedtuple

from pyatv.support import udns

_LOGGER = logging.getLogger(__name__)

DEFAULT_QCLASS = 1
DEFAULT_TTL = 10

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


def _mkanswer(qname, full_name):
    return udns.DnsAnswer(
        qname, udns.QTYPE_PTR, DEFAULT_QCLASS, DEFAULT_TTL, 0, full_name
    )


def _mkresource(qname, qtype, rd):
    return udns.DnsResource(qname, qtype, DEFAULT_QCLASS, DEFAULT_TTL, len(rd), rd)


def _mkproperties(properties):
    rd = b""
    for k, v in properties.items():
        encoded = (k + "=" + v).encode("ascii")
        rd += bytes([len(encoded)]) + encoded
    return rd


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
            resp.answers.append(_mkanswer(question.qname, full_name))

            # Add service (SRV) resource
            if service.port:
                local_name = udns.qname_encode(service.name + ".local")
                rd = struct.pack(">3H", 0, 0, service.port) + local_name
                resp.resources.append(_mkresource(full_name, udns.QTYPE_SRV, rd))

            # Add properties
            if service.properties:
                rd = _mkproperties(service.properties)
                resp.resources.append(_mkresource(full_name, udns.QTYPE_TXT, rd))

        self.transport.sendto(resp.pack(), addr)


@contextmanager
def stub_multicast(udns_server, loop):
    patcher = patch("pyatv.support.udns.multicast")

    async def _multicast(loop, services, **kwargs):
        hosts = set(service.address for service in udns_server.services.values())
        devices = []
        for host in hosts:
            udns_server.ip_filter = host
            devices.append(
                (
                    IPv4Address(host),
                    await udns.unicast(
                        loop, "127.0.0.1", services, port=udns_server.port
                    ),
                )
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
