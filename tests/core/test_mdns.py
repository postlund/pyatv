"""Unit tests pyatv.core.mdns."""

import asyncio
import io
from ipaddress import IPv4Address
import logging
from typing import List, Optional, Tuple

import pytest

from pyatv.core import mdns
from pyatv.support import dns, net

from tests import fake_udns
from tests.support import dns_utils

SERVICE_NAME = "Kitchen"
MEDIAREMOTE_SERVICE = "_mediaremotetv._tcp.local"
DEVICE_INFO_SERVICE = "_device-info._tcp._local"


TEST_SERVICES = dict(
    [
        fake_udns.mrp_service(
            SERVICE_NAME, SERVICE_NAME, "mrp_id", addresses=["127.0.0.1"], port=1234
        ),
    ]
)


def get_response_for_service(
    service: str,
) -> Tuple[dns.DnsMessage, Optional[fake_udns.FakeDnsService]]:
    req = mdns.create_service_queries([service], mdns.QueryType.PTR)[0]
    resp = fake_udns.create_response(req, TEST_SERVICES)
    return dns.DnsMessage().unpack(resp.pack()), TEST_SERVICES.get(service)


def parse_services(message: mdns.DnsMessage) -> List[mdns.Service]:
    parser = mdns.ServiceParser()
    parser.add_message(message)
    return parser.parse()


def test_non_existing_service():
    resp, _ = get_response_for_service("_missing")
    assert len(resp.questions) == 2
    assert len(resp.answers) == 0
    assert len(resp.resources) == 0


def test_service_has_expected_responses():
    resp, _ = get_response_for_service(MEDIAREMOTE_SERVICE)
    assert len(resp.questions) == 2
    assert len(resp.answers) == 1
    assert len(resp.resources) == 3


def test_service_has_valid_question():
    resp, _ = get_response_for_service(MEDIAREMOTE_SERVICE)
    question = resp.questions[0]
    assert question.qname == MEDIAREMOTE_SERVICE
    assert question.qtype == dns.QueryType.PTR
    assert question.qclass == 0x8001


def test_service_has_valid_answer():
    resp, data = get_response_for_service(MEDIAREMOTE_SERVICE)
    answer = resp.answers[0]
    assert answer.qname == MEDIAREMOTE_SERVICE
    assert answer.qtype == dns.QueryType.PTR
    assert answer.qclass == dns_utils.DEFAULT_QCLASS
    assert answer.ttl == dns_utils.DEFAULT_TTL
    assert answer.rd == data.name + "." + MEDIAREMOTE_SERVICE


def test_service_has_valid_srv_resource():
    resp, data = get_response_for_service(MEDIAREMOTE_SERVICE)

    srv = dns_utils.get_qtype(resp.resources, dns.QueryType.SRV)
    assert srv.qname == data.name + "." + MEDIAREMOTE_SERVICE
    assert srv.qtype == dns.QueryType.SRV
    assert srv.qclass == dns_utils.DEFAULT_QCLASS
    assert srv.ttl == dns_utils.DEFAULT_TTL

    rd = srv.rd
    assert rd["priority"] == 0
    assert rd["weight"] == 0
    assert rd["port"] == data.port
    assert rd["target"] == data.name + ".local"


def test_service_has_valid_txt_resource():
    resp, data = get_response_for_service(MEDIAREMOTE_SERVICE)

    srv = dns_utils.get_qtype(resp.resources, dns.QueryType.TXT)
    assert srv.qname == data.name + "." + MEDIAREMOTE_SERVICE
    assert srv.qtype == dns.QueryType.TXT
    assert srv.qclass == dns_utils.DEFAULT_QCLASS
    assert srv.ttl == dns_utils.DEFAULT_TTL

    rd = srv.rd
    assert len(rd) == len(data.properties)
    for k, v in data.properties.items():
        assert rd[k] == v


def test_service_has_valid_a_resource():
    resp, data = get_response_for_service(MEDIAREMOTE_SERVICE)

    srv = dns_utils.get_qtype(resp.resources, dns.QueryType.A)
    assert srv.qname == data.name + ".local"
    assert srv.qtype == dns.QueryType.A
    assert srv.qclass == dns_utils.DEFAULT_QCLASS
    assert srv.ttl == dns_utils.DEFAULT_TTL
    assert srv.rd == "127.0.0.1"


def test_authority():
    msg = dns.DnsMessage()
    msg.authorities.append(
        dns_utils.resource("test.local", dns.QueryType.A, b"\x01\x02\x03\x04")
    )

    unpacked = dns.DnsMessage().unpack(msg.pack())
    assert len(unpacked.authorities) == 1

    record = unpacked.authorities[0]
    assert record.qname == "test.local"
    assert record.qtype == dns.QueryType.A
    assert record.qclass == dns_utils.DEFAULT_QCLASS
    assert record.ttl == dns_utils.DEFAULT_TTL
    assert record.rd == "1.2.3.4"


def test_parse_empty_service():
    assert parse_services(dns.DnsMessage()) == []


def test_parse_no_service_type():
    service_params = (None, "service", [], 0, {})
    message = dns_utils.add_service(dns.DnsMessage(), *service_params)

    parsed = parse_services(message)
    assert len(parsed) == 0


def test_parse_no_service_name():
    service_params = ("_abc._tcp.local", None, [], 0, {})
    message = dns_utils.add_service(dns.DnsMessage(), *service_params)

    parsed = parse_services(message)
    assert len(parsed) == 0


def test_parse_with_name_and_type():
    service_params = ("_abc._tcp.local", "service", [], 0, {})
    message = dns_utils.add_service(dns.DnsMessage(), *service_params)

    parsed = parse_services(message)
    assert len(parsed) == 1
    dns_utils.assert_service(parsed[0], *service_params)


def test_parse_with_port_and_address():
    service_params = ("_abc._tcp.local", "service", ["10.0.0.1"], 123, {})
    message = dns_utils.add_service(dns.DnsMessage(), *service_params)

    parsed = parse_services(message)
    assert len(parsed) == 1
    dns_utils.assert_service(parsed[0], *service_params)


def test_parse_single_service():
    service_params = ("_abc._tcp.local", "service", ["10.0.10.1"], 123, {"foo": "bar"})
    message = dns_utils.add_service(dns.DnsMessage(), *service_params)

    parsed = parse_services(message)
    assert len(parsed) == 1
    dns_utils.assert_service(parsed[0], *service_params)


def test_parse_double_service():
    service1_params = (
        "_abc._tcp.local",
        "service1",
        ["10.0.10.1"],
        123,
        {"foo": "bar"},
    )
    service2_params = (
        "_def._tcp.local",
        "service2",
        ["10.0.10.2"],
        456,
        {"fizz": "buzz"},
    )
    message = dns_utils.add_service(dns.DnsMessage(), *service1_params)
    message = dns_utils.add_service(message, *service2_params)

    parsed = parse_services(message)
    assert len(parsed) == 2
    dns_utils.assert_service(parsed[0], *service1_params)
    dns_utils.assert_service(parsed[1], *service2_params)


def test_parse_pick_one_available_address():
    addresses = ["10.0.10.1", "10.0.10.2"]
    service_params = (
        "_abc._tcp.local",
        "service",
        addresses,
        123,
        {"foo": "bar"},
    )
    message = dns_utils.add_service(dns.DnsMessage(), *service_params)

    parsed = parse_services(message)
    assert len(parsed) == 1
    assert str(parsed[0].address) in addresses


def test_parse_ignore_link_local_address():
    service_params = (
        "_abc._tcp.local",
        "service",
        ["169.254.1.1"],
        123,
        {"foo": "bar"},
    )
    message = dns_utils.add_service(dns.DnsMessage(), *service_params)

    parsed = parse_services(message)
    assert len(parsed) == 1
    assert parsed[0].address is None


# Note: This is an unwanted side-effect of using CaseInsensitiveDict. It's very
# unlikely that two properties will ever exist, only differ in case and is because of
# that not a big problem. But a test should exist for it to make sure we don't break
# anything in the future.
def test_parse_properties_converts_keys_to_lower_case():
    service_params = ("_abc._tcp.local", "service", [], 0, {"FOO": "bar", "Bar": "FOO"})
    message = dns_utils.add_service(dns.DnsMessage(), *service_params)

    parsed = parse_services(message)
    assert len(parsed) == 1
    assert parsed[0].properties["foo"] == "bar"
    assert parsed[0].properties["Bar"] == "FOO"


def test_parse_ignore_duplicate_records():
    service_params = ("_abc._tcp.local", "service", [], 0, {})
    message = dns_utils.add_service(dns.DnsMessage(), *service_params)

    parser = mdns.ServiceParser()
    parser.add_message(message)
    parser.add_message(message)

    # One service should be present in the table
    assert len(parser.table) == 1

    # A single record should be there since duplicates is ignored
    records = parser.table["service._abc._tcp.local"]
    assert mdns.QueryType.SRV in records
    assert len(records[mdns.QueryType.SRV]) == 1
