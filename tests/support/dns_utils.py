"""Helper methods for DNS messages."""

import struct
from pyatv.support import udns

DEFAULT_QCLASS = 1
DEFAULT_TTL = 10


def answer(qname, full_name):
    return udns.DnsAnswer(
        qname, udns.QTYPE_PTR, DEFAULT_QCLASS, DEFAULT_TTL, 0, full_name
    )


def resource(qname, qtype, rd):
    return udns.DnsResource(qname, qtype, DEFAULT_QCLASS, DEFAULT_TTL, len(rd), rd)


def properties(properties):
    rd = b""
    for k, v in properties.items():
        encoded = (k + "=" + v).encode("ascii")
        rd += bytes([len(encoded)]) + encoded
    return rd
