"""Helper methods for DNS message."""

import struct
from ipaddress import IPv4Address
from typing import Optional, Dict
from pyatv.support import mdns

DEFAULT_QCLASS = 1
DEFAULT_TTL = 10


def answer(qname: str, full_name: str) -> mdns.DnsResource:
    return mdns.DnsResource(
        qname, mdns.QTYPE_PTR, DEFAULT_QCLASS, DEFAULT_TTL, 0, full_name
    )


def resource(qname: str, qtype: int, rd) -> mdns.DnsResource:
    return mdns.DnsResource(qname, qtype, DEFAULT_QCLASS, DEFAULT_TTL, len(rd), rd)


def properties(properties: Dict[bytes, bytes]) -> bytes:
    rd = b""
    for k, v in properties.items():
        encoded = k + b"=" + v
        rd += bytes([len(encoded)]) + encoded
    return rd


def get_qtype(messages: mdns.DnsMessage, qtype: int) -> Optional[mdns.DnsResource]:
    for message in messages:
        if message.qtype == qtype:
            return message
    return None


def add_service(
    message: mdns.DnsMessage,
    service_type: Optional[str],
    service_name: Optional[str],
    address: Optional[str],
    port: int,
    properties: dict,
) -> None:
    if service_name is None:
        return message

    if address:
        message.resources.append(
            resource(service_name + ".local", mdns.QTYPE_A, address)
        )

    # Remaining depends on service type
    if service_type is None:
        return message

    message.answers.append(answer(service_type, service_name + "." + service_type))

    message.resources.append(
        resource(
            service_name + "." + service_type,
            mdns.QTYPE_SRV,
            {
                "priority": 0,
                "weight": 0,
                "port": port,
                "target": service_name + ".local",
            },
        )
    )

    if properties:
        message.resources.append(
            resource(
                service_name + "." + service_type,
                mdns.QTYPE_TXT,
                {k.encode("utf-8"): v.encode("utf-8") for k, v in properties.items()},
            )
        )

    return message


def assert_service(
    message: mdns.DnsMessage,
    service_type: str,
    service_name: str,
    address: str,
    port: int,
    properties: dict,
) -> None:
    assert message.type == service_type
    assert message.name == service_name
    assert message.address == (IPv4Address(address) if address else None)
    assert message.port == port
    assert message.properties == properties
