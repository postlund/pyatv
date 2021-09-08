"""Helper methods for DNS message."""

from ipaddress import IPv4Address
import struct
from typing import Dict, List, Optional

from pyatv.core import mdns
from pyatv.support import dns

DEFAULT_QCLASS = 1
DEFAULT_TTL = 10


def answer(qname: str, full_name: str) -> mdns.DnsResource:
    return mdns.DnsResource(
        qname, mdns.QueryType.PTR, DEFAULT_QCLASS, DEFAULT_TTL, 0, full_name
    )


def resource(qname: str, qtype: mdns.QueryType, rd) -> mdns.DnsResource:
    return mdns.DnsResource(qname, qtype, DEFAULT_QCLASS, DEFAULT_TTL, len(rd), rd)


def properties(properties: Dict[str, bytes]) -> bytes:
    rd = b""
    for k, v in properties.items():
        encoded = k.encode("ascii") + b"=" + v
        rd += bytes([len(encoded)]) + encoded
    return rd


def get_qtype(
    messages: List[mdns.DnsResource], qtype: int
) -> Optional[mdns.DnsResource]:
    for message in messages:
        if message.qtype == qtype:
            return message
    return None


def add_service(
    message: mdns.DnsMessage,
    service_type: Optional[str],
    service_name: Optional[str],
    addresses: List[str],
    port: int,
    properties: Dict[str, bytes],
) -> None:
    if service_name is None:
        return message

    for address in addresses:
        message.resources.append(
            resource(service_name + ".local", mdns.QueryType.A, address)
        )

    # Remaining depends on service type
    if service_type is None:
        return message

    message.answers.append(answer(service_type, service_name + "." + service_type))

    message.resources.append(
        resource(
            service_name + "." + service_type,
            mdns.QueryType.SRV,
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
                mdns.QueryType.TXT,
                {k: v.encode("utf-8") for k, v in properties.items()},
            )
        )

    return message


def assert_service(
    message: mdns.Service,
    service_type: str,
    service_name: str,
    addresses: List[str],
    port: int,
    known_properties: Dict[str, bytes],
) -> None:
    assert message.type == service_type
    assert message.name == service_name

    # Assume first address (if multiple) is expected
    assert message.address == (IPv4Address(addresses[0]) if addresses else None)
    assert message.port == port
    assert message.properties == known_properties
