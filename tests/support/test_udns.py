"""Functional tests for unicast DNS."""

import asyncio
import logging
from ipaddress import IPv4Address
from unittest.mock import patch

import pytest

from pyatv import exceptions
from pyatv.support import udns
from tests import fake_udns


MEDIAREMOTE_SERVICE = "_mediaremotetv._tcp.local"

TEST_SERVICES = {
    MEDIAREMOTE_SERVICE: fake_udns.FakeDnsService(
        name="Kitchen",
        address="127.0.0.1",
        port=1234,
        properties={"Name": "Kitchen", "foo": "=bar"},
    ),
}


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
# responses and abort the "waiting" period whenever all responses have been received.
# Mainly this is for not slowing down tests.
@pytest.fixture
async def multicast_fastexit(event_loop, monkeypatch):
    # Interface used to set number of expected responses (1 by default)
    expected_responses = [1]

    def _set_expected_responses(responses):
        expected_responses[0] = responses

    # Replace create_datagram_endpoint with a method that captures the created
    # endpoints and use a simple poller to detect if all responses have been received
    create_endpoint = event_loop.create_datagram_endpoint

    async def _create_datagram_endpoint(factory, **kwargs):
        transport, protocol = await create_endpoint(factory, **kwargs)

        async def _poll_responses():
            while len(protocol.responses) != expected_responses[0]:
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
        await udns.unicast(
            event_loop,
            "127.0.0.1",
            [service_name],
            port=udns_server.port,
            timeout=timeout,
        ),
        TEST_SERVICES.get(service_name),
    )


def get_qtype(messages, qtype):
    for message in messages:
        if message.qtype == qtype:
            return message
    return None


def test_qname_with_label():
    # This should resolve to "label.test" when reading from \x05
    message = b"aaaa" + b"\x04test\x00" + b"\x05label\xC0\x04\xAB\xCD"
    ptr = message[10:]
    ret, rest = udns.qname_decode(ptr, message)
    assert ret == "label.test"
    assert rest == b"\xAB\xCD"


@pytest.mark.asyncio
async def test_non_local_address(event_loop, stub_local_address):
    stub_local_address.return_value = None
    with pytest.raises(exceptions.NonLocalSubnetError):
        await udns.unicast(event_loop, "1.2.3.4", [])


@pytest.mark.asyncio
async def test_non_existing_service(event_loop, udns_server):
    resp, _ = await unicast(event_loop, udns_server, "_missing")
    assert len(resp.questions) == 1
    assert len(resp.answers) == 0
    assert len(resp.resources) == 0


@pytest.mark.asyncio
async def test_service_has_expected_responses(event_loop, udns_server):
    resp, _ = await unicast(event_loop, udns_server, MEDIAREMOTE_SERVICE)
    assert len(resp.questions) == 1
    assert len(resp.answers) == 1
    assert len(resp.resources) == 2


@pytest.mark.asyncio
async def test_service_has_valid_question(event_loop, udns_server):
    resp, _ = await unicast(event_loop, udns_server, MEDIAREMOTE_SERVICE)

    question = resp.questions[0]
    assert question.qname == MEDIAREMOTE_SERVICE
    assert question.qtype == udns.QTYPE_ANY
    assert question.qclass == 0x8001


@pytest.mark.asyncio
async def test_service_has_valid_answer(event_loop, udns_server):
    resp, data = await unicast(event_loop, udns_server, MEDIAREMOTE_SERVICE)

    answer = resp.answers[0]
    assert answer.qname == MEDIAREMOTE_SERVICE
    assert answer.qtype == udns.QTYPE_PTR
    assert answer.qclass == fake_udns.DEFAULT_QCLASS
    assert answer.ttl == fake_udns.DEFAULT_TTL
    assert answer.rd == data.name + "." + MEDIAREMOTE_SERVICE


@pytest.mark.asyncio
async def test_service_has_valid_srv_resource(event_loop, udns_server):
    resp, data = await unicast(event_loop, udns_server, MEDIAREMOTE_SERVICE)

    srv = get_qtype(resp.resources, udns.QTYPE_SRV)
    assert srv.qname == data.name + "." + MEDIAREMOTE_SERVICE
    assert srv.qtype == udns.QTYPE_SRV
    assert srv.qclass == fake_udns.DEFAULT_QCLASS
    assert srv.ttl == fake_udns.DEFAULT_TTL

    rd = srv.rd
    assert rd["priority"] == 0
    assert rd["weight"] == 0
    assert rd["port"] == data.port
    assert rd["target"] == data.name + ".local"


@pytest.mark.asyncio
async def test_service_has_valid_txt_resource(event_loop, udns_server):
    resp, data = await unicast(event_loop, udns_server, MEDIAREMOTE_SERVICE)

    srv = get_qtype(resp.resources, udns.QTYPE_TXT)
    assert srv.qname == data.name + "." + MEDIAREMOTE_SERVICE
    assert srv.qtype == udns.QTYPE_TXT
    assert srv.qclass == fake_udns.DEFAULT_QCLASS
    assert srv.ttl == fake_udns.DEFAULT_TTL

    rd = srv.rd
    assert len(rd) == len(data.properties)
    for k, v in data.properties.items():
        assert rd[k.encode("ascii")] == v.encode("ascii")


@pytest.mark.asyncio
async def test_resend_if_no_response(event_loop, udns_server):
    udns_server.skip_count = 2
    resp, _ = await unicast(event_loop, udns_server, MEDIAREMOTE_SERVICE, 3)
    assert len(resp.questions) == 1
    assert len(resp.answers) == 1
    assert len(resp.resources) == 2


@pytest.mark.asyncio
async def test_multicast_no_response(event_loop, udns_server, multicast_fastexit):
    multicast_fastexit(0)
    await udns.multicast(event_loop, [], "127.0.0.1", udns_server.port)


@pytest.mark.asyncio
async def test_multicast_has_valid_response(
    event_loop, udns_server, multicast_fastexit
):
    multicast_fastexit(1)

    resp = await udns.multicast(
        event_loop, [MEDIAREMOTE_SERVICE], "127.0.0.1", udns_server.port
    )
    assert len(resp) == 1

    first = resp[IPv4Address("127.0.0.1")]
    assert len(first.questions) == 1
    assert len(first.answers) == 1
    assert len(first.resources) == 2
