"""Unit tests pyatv.support.mdns."""

import asyncio
import logging
from typing import Tuple
from ipaddress import IPv4Address

import pytest

from pyatv.support import mdns, net
from tests import fake_udns
from tests.support import dns_utils


SERVICE_NAME = "Kitchen"
MEDIAREMOTE_SERVICE = "_mediaremotetv._tcp.local"
DEVICE_INFO_SERVICE = "_device-info._tcp._local"


TEST_SERVICES = dict(
    [
        fake_udns.mrp_service(
            SERVICE_NAME, SERVICE_NAME, "mrp_id", address="127.0.0.1", port=1234
        ),
    ]
)


def get_response_for_service(
    service: str,
) -> Tuple[mdns.DnsMessage, fake_udns.FakeDnsService]:
    req = mdns.create_request([service])
    resp = fake_udns.create_response(req, TEST_SERVICES)
    return mdns.DnsMessage().unpack(resp.pack()), TEST_SERVICES.get(service)


def test_qname_with_label():
    # This should resolve to "label.test" when reading from \x05
    message = b"aaaa" + b"\x04test\x00" + b"\x05label\xC0\x04\xAB\xCD"
    ptr = message[10:]
    ret, rest = mdns.qname_decode(ptr, message)
    assert ret == "label.test"
    assert rest == b"\xAB\xCD"


def test_non_existing_service():
    resp, _ = get_response_for_service("_missing")
    assert len(resp.questions) == 1
    assert len(resp.answers) == 0
    assert len(resp.resources) == 0


def test_service_has_expected_responses():
    resp, _ = get_response_for_service(MEDIAREMOTE_SERVICE)
    assert len(resp.questions) == 1
    assert len(resp.answers) == 1
    assert len(resp.resources) == 3


def test_service_has_valid_question():
    resp, _ = get_response_for_service(MEDIAREMOTE_SERVICE)
    question = resp.questions[0]
    assert question.qname == MEDIAREMOTE_SERVICE
    assert question.qtype == mdns.QTYPE_PTR
    assert question.qclass == 0x8001


def test_service_has_valid_answer():
    resp, data = get_response_for_service(MEDIAREMOTE_SERVICE)
    answer = resp.answers[0]
    assert answer.qname == MEDIAREMOTE_SERVICE
    assert answer.qtype == mdns.QTYPE_PTR
    assert answer.qclass == dns_utils.DEFAULT_QCLASS
    assert answer.ttl == dns_utils.DEFAULT_TTL
    assert answer.rd == data.name + "." + MEDIAREMOTE_SERVICE


def test_service_has_valid_srv_resource():
    resp, data = get_response_for_service(MEDIAREMOTE_SERVICE)

    srv = dns_utils.get_qtype(resp.resources, mdns.QTYPE_SRV)
    assert srv.qname == data.name + "." + MEDIAREMOTE_SERVICE
    assert srv.qtype == mdns.QTYPE_SRV
    assert srv.qclass == dns_utils.DEFAULT_QCLASS
    assert srv.ttl == dns_utils.DEFAULT_TTL

    rd = srv.rd
    assert rd["priority"] == 0
    assert rd["weight"] == 0
    assert rd["port"] == data.port
    assert rd["target"] == data.name + ".local"


def test_service_has_valid_txt_resource():
    resp, data = get_response_for_service(MEDIAREMOTE_SERVICE)

    srv = dns_utils.get_qtype(resp.resources, mdns.QTYPE_TXT)
    assert srv.qname == data.name + "." + MEDIAREMOTE_SERVICE
    assert srv.qtype == mdns.QTYPE_TXT
    assert srv.qclass == dns_utils.DEFAULT_QCLASS
    assert srv.ttl == dns_utils.DEFAULT_TTL

    rd = srv.rd
    assert len(rd) == len(data.properties)
    for k, v in data.properties.items():
        assert rd[k] == v


def test_service_has_valid_a_resource():
    resp, data = get_response_for_service(MEDIAREMOTE_SERVICE)

    srv = dns_utils.get_qtype(resp.resources, mdns.QTYPE_A)
    assert srv.qname == data.name + ".local"
    assert srv.qtype == mdns.QTYPE_A
    assert srv.qclass == dns_utils.DEFAULT_QCLASS
    assert srv.ttl == dns_utils.DEFAULT_TTL
    assert srv.rd == "127.0.0.1"


def test_authority():
    msg = mdns.DnsMessage()
    msg.authorities.append(
        dns_utils.resource("test.local", mdns.QTYPE_A, b"\x01\x02\x03\x04")
    )

    unpacked = mdns.DnsMessage().unpack(msg.pack())
    assert len(unpacked.authorities) == 1

    record = unpacked.authorities[0]
    assert record.qname == "test.local"
    assert record.qtype == mdns.QTYPE_A
    assert record.qclass == dns_utils.DEFAULT_QCLASS
    assert record.ttl == dns_utils.DEFAULT_TTL
    assert record.rd == "1.2.3.4"


def test_parse_empty_service():
    assert mdns.parse_services(mdns.DnsMessage()) == []


def test_parse_no_service_type():
    service_params = (None, "service", None, 0, {})
    message = dns_utils.add_service(mdns.DnsMessage(), *service_params)

    parsed = mdns.parse_services(message)
    assert len(parsed) == 0


def test_parse_no_service_name():
    service_params = ("_abc._tcp.local", None, None, 0, {})
    message = dns_utils.add_service(mdns.DnsMessage(), *service_params)

    parsed = mdns.parse_services(message)
    assert len(parsed) == 0


def test_parse_with_name_and_type():
    service_params = ("_abc._tcp.local", "service", None, 0, {})
    message = dns_utils.add_service(mdns.DnsMessage(), *service_params)

    parsed = mdns.parse_services(message)
    assert len(parsed) == 1
    dns_utils.assert_service(parsed[0], *service_params)


def test_parse_with_port_and_address():
    service_params = ("_abc._tcp.local", "service", "10.0.0.1", 123, {})
    message = dns_utils.add_service(mdns.DnsMessage(), *service_params)

    parsed = mdns.parse_services(message)
    assert len(parsed) == 1
    dns_utils.assert_service(parsed[0], *service_params)


def test_parse_single_service():
    service_params = ("_abc._tcp.local", "service", "10.0.10.1", 123, {"foo": "bar"})
    message = dns_utils.add_service(mdns.DnsMessage(), *service_params)

    parsed = mdns.parse_services(message)
    assert len(parsed) == 1
    dns_utils.assert_service(parsed[0], *service_params)


def test_parse_double_service():
    service1_params = ("_abc._tcp.local", "service1", "10.0.10.1", 123, {"foo": "bar"})
    service2_params = (
        "_def._tcp.local",
        "service2",
        "10.0.10.2",
        456,
        {"fizz": "buzz"},
    )
    message = dns_utils.add_service(mdns.DnsMessage(), *service1_params)
    message = dns_utils.add_service(message, *service2_params)

    parsed = mdns.parse_services(message)
    assert len(parsed) == 2
    dns_utils.assert_service(parsed[0], *service1_params)
    dns_utils.assert_service(parsed[1], *service2_params)
