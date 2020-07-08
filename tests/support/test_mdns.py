"""Functional tests pyatv.support.mdns."""

import asyncio
import logging
from copy import deepcopy
from typing import Optional, Tuple
from ipaddress import IPv4Address
from unittest.mock import patch

import pytest

from pyatv import exceptions
from pyatv.support import mdns
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


@pytest.fixture(autouse=True)
def stub_local_address():
    with patch("pyatv.net.get_local_address_reaching") as mock:
        mock.return_value = IPv4Address("127.0.0.1")
        yield mock


@pytest.fixture
async def udns_server(event_loop):
    server = fake_udns.FakeUdns(event_loop, TEST_SERVICES)
    await server.start()
    yield server
    server.close()


# This is a very complex fixture that will hook into the receiver of multicast
# responses and abort the "waiting" period whenever all responses or a certain amount
# of requests have been received. Mainly this is for not slowing down tests.
@pytest.fixture
async def multicast_fastexit(event_loop, monkeypatch, udns_server):
    # Interface used to set number of expected responses (1 by default)
    expected_responses: List[int] = [1, 0]

    def _set_expected_responses(response_count: int, request_count: int):
        expected_responses[0] = response_count
        expected_responses[1] = request_count

    # Checks if either response or request count has been fulfilled
    def _check_cond(protocol: mdns.MulticastDnsSdClientProtocol) -> bool:
        if len(protocol.responses) == expected_responses[0]:
            return False
        if expected_responses[1] == 0:
            return True
        return udns_server.request_count < expected_responses[1]

    # Replace create_datagram_endpoint with a method that captures the created
    # endpoints and use a simple poller to detect if all responses have been received
    create_endpoint = event_loop.create_datagram_endpoint

    async def _create_datagram_endpoint(factory, **kwargs):
        transport, protocol = await create_endpoint(factory, **kwargs)

        async def _poll_responses():
            while _check_cond(protocol):
                await asyncio.sleep(0.1)
            protocol.semaphore.release()

        asyncio.ensure_future(_poll_responses())

        return transport, protocol

    monkeypatch.setattr(
        event_loop, "create_datagram_endpoint", _create_datagram_endpoint
    )

    yield _set_expected_responses


async def unicast(event_loop, udns_server, service_name, timeout=1):
    return (
        await mdns.unicast(
            event_loop,
            "127.0.0.1",
            [service_name],
            port=udns_server.port,
            timeout=timeout,
        ),
        TEST_SERVICES.get(service_name),
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


@pytest.mark.asyncio
async def test_non_local_address(event_loop, stub_local_address):
    stub_local_address.return_value = None
    with pytest.raises(exceptions.NonLocalSubnetError):
        await mdns.unicast(event_loop, "1.2.3.4", [])


@pytest.mark.asyncio
async def test_non_existing_service():
    resp, _ = get_response_for_service("_missing")
    assert len(resp.questions) == 1
    assert len(resp.answers) == 0
    assert len(resp.resources) == 0


@pytest.mark.asyncio
async def test_service_has_expected_responses():
    resp, _ = get_response_for_service(MEDIAREMOTE_SERVICE)
    assert len(resp.questions) == 1
    assert len(resp.answers) == 1
    assert len(resp.resources) == 3


@pytest.mark.asyncio
async def test_service_has_valid_question():
    resp, _ = get_response_for_service(MEDIAREMOTE_SERVICE)
    question = resp.questions[0]
    assert question.qname == MEDIAREMOTE_SERVICE
    assert question.qtype == mdns.QTYPE_ANY
    assert question.qclass == 0x8001


@pytest.mark.asyncio
async def test_service_has_valid_answer():
    resp, data = get_response_for_service(MEDIAREMOTE_SERVICE)
    answer = resp.answers[0]
    assert answer.qname == MEDIAREMOTE_SERVICE
    assert answer.qtype == mdns.QTYPE_PTR
    assert answer.qclass == dns_utils.DEFAULT_QCLASS
    assert answer.ttl == dns_utils.DEFAULT_TTL
    assert answer.rd == data.name + "." + MEDIAREMOTE_SERVICE


@pytest.mark.asyncio
async def test_service_has_valid_srv_resource():
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


@pytest.mark.asyncio
async def test_service_has_valid_txt_resource():
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


@pytest.mark.asyncio
async def test_service_has_valid_a_resource():
    resp, data = get_response_for_service(MEDIAREMOTE_SERVICE)

    srv = dns_utils.get_qtype(resp.resources, mdns.QTYPE_A)
    assert srv.qname == data.name + ".local"
    assert srv.qtype == mdns.QTYPE_A
    assert srv.qclass == dns_utils.DEFAULT_QCLASS
    assert srv.ttl == dns_utils.DEFAULT_TTL
    assert srv.rd == "127.0.0.1"


@pytest.mark.asyncio
async def test_unicast_has_valid_service(event_loop, udns_server):
    resp, service = await unicast(event_loop, udns_server, MEDIAREMOTE_SERVICE)
    assert len(resp.services) == 1
    assert resp.services[0].type == MEDIAREMOTE_SERVICE
    assert resp.services[0].name == service.name
    assert resp.services[0].port == service.port


@pytest.mark.asyncio
async def test_unicast_resend_if_no_response(event_loop, udns_server):
    udns_server.skip_count = 2
    resp, service = await unicast(event_loop, udns_server, MEDIAREMOTE_SERVICE, 3)
    assert len(resp.services) == 1
    assert resp.services[0].type == MEDIAREMOTE_SERVICE
    assert resp.services[0].name == service.name
    assert resp.services[0].port == service.port


@pytest.mark.asyncio
async def test_unicast_specific_service(event_loop, udns_server):
    resp, _ = await unicast(
        event_loop, udns_server, SERVICE_NAME + "." + MEDIAREMOTE_SERVICE
    )
    assert len(resp.services) == 1

    service = TEST_SERVICES.get(MEDIAREMOTE_SERVICE)
    assert resp.services[0].type == MEDIAREMOTE_SERVICE
    assert resp.services[0].name == service.name
    assert resp.services[0].port == service.port


@pytest.mark.asyncio
async def test_multicast_no_response(event_loop, udns_server, multicast_fastexit):
    multicast_fastexit(0, 0)

    await mdns.multicast(event_loop, [], "127.0.0.1", udns_server.port)


@pytest.mark.asyncio
async def test_multicast_has_valid_service(event_loop, udns_server, multicast_fastexit):
    multicast_fastexit(1, 0)

    resp = await mdns.multicast(
        event_loop, [MEDIAREMOTE_SERVICE], "127.0.0.1", udns_server.port
    )
    assert len(resp) == 1

    first = resp[IPv4Address("127.0.0.1")].services[0]
    assert first.type == MEDIAREMOTE_SERVICE
    assert first.name == SERVICE_NAME
    assert first.port == 1234


@pytest.mark.asyncio
async def test_multicast_sleeping_device(event_loop, udns_server, multicast_fastexit):
    multicast_fastexit(0, 3)
    udns_server.sleep_proxy = True

    udns_server.services = {
        MEDIAREMOTE_SERVICE: fake_udns.FakeDnsService(
            name=SERVICE_NAME, address=None, port=0, properties={}, model=None
        ),
    }

    resp = await mdns.multicast(
        event_loop, [MEDIAREMOTE_SERVICE], "127.0.0.1", udns_server.port
    )
    assert len(resp) == 0

    multicast_fastexit(1, 0)
    udns_server.services = TEST_SERVICES

    resp = await mdns.multicast(
        event_loop, [MEDIAREMOTE_SERVICE], "127.0.0.1", udns_server.port
    )
    assert len(resp) == 1


@pytest.mark.asyncio
async def test_multicast_deep_sleep(event_loop, udns_server, multicast_fastexit):
    multicast_fastexit(1, 0)

    resp = await mdns.multicast(
        event_loop, [MEDIAREMOTE_SERVICE], "127.0.0.1", udns_server.port
    )

    assert not resp[IPv4Address("127.0.0.1")].deep_sleep

    udns_server.sleep_proxy = True
    multicast_fastexit(1, 0)

    resp = await mdns.multicast(
        event_loop, [MEDIAREMOTE_SERVICE], "127.0.0.1", udns_server.port
    )

    assert resp[IPv4Address("127.0.0.1")].deep_sleep


@pytest.mark.asyncio
async def test_multicast_device_model(event_loop, udns_server, multicast_fastexit):
    multicast_fastexit(1, 0)

    resp = await mdns.multicast(
        event_loop, [MEDIAREMOTE_SERVICE], "127.0.0.1", udns_server.port
    )

    assert not resp[IPv4Address("127.0.0.1")].model

    udns_server.services = {
        MEDIAREMOTE_SERVICE: fake_udns.FakeDnsService(
            name=SERVICE_NAME,
            address="127.0.0.1",
            port=1234,
            properties={},
            model="dummy",
        ),
    }
    multicast_fastexit(1, 0)

    resp = await mdns.multicast(
        event_loop, [MEDIAREMOTE_SERVICE], "127.0.0.1", udns_server.port
    )

    assert resp[IPv4Address("127.0.0.1")].model == "dummy"


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
