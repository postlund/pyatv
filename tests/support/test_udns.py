"""Functional tests for unicast DNS."""

import pytest

from pyatv.support import udns
from tests import fake_udns


MEDIAREMOTE_SERVICE = "_mediaremotetv._tcp.local"

TEST_SERVICES = {
    MEDIAREMOTE_SERVICE: fake_udns.FakeDnsService(
        name="Kitchen", port=1234, properties={"Name": "Kitchen", "foo": "=bar"}
    ),
}


@pytest.fixture
async def udns_server(event_loop):
    server = fake_udns.FakeUdns(event_loop, TEST_SERVICES)
    await server.start()
    yield server
    server.close()


async def request(event_loop, udns_server, service_name):
    return (
        await udns.request(
            event_loop, "127.0.0.1", [service_name], port=udns_server.port, timeout=1
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
async def test_non_existing_service(event_loop, udns_server):
    resp, _ = await request(event_loop, udns_server, "_missing")
    assert len(resp.questions) == 1
    assert len(resp.answers) == 0
    assert len(resp.resources) == 0


@pytest.mark.asyncio
async def test_service_has_expected_responses(event_loop, udns_server):
    resp, _ = await request(event_loop, udns_server, MEDIAREMOTE_SERVICE)
    assert len(resp.questions) == 1
    assert len(resp.answers) == 1
    assert len(resp.resources) == 2


@pytest.mark.asyncio
async def test_service_has_valid_question(event_loop, udns_server):
    resp, _ = await request(event_loop, udns_server, MEDIAREMOTE_SERVICE)

    question = resp.questions[0]
    assert question.qname == MEDIAREMOTE_SERVICE
    assert question.qtype == udns.QTYPE_ANY
    assert question.qclass == 0x8001


@pytest.mark.asyncio
async def test_service_has_valid_answer(event_loop, udns_server):
    resp, data = await request(event_loop, udns_server, MEDIAREMOTE_SERVICE)

    answer = resp.answers[0]
    assert answer.qname == MEDIAREMOTE_SERVICE
    assert answer.qtype == udns.QTYPE_PTR
    assert answer.qclass == fake_udns.DEFAULT_QCLASS
    assert answer.ttl == fake_udns.DEFAULT_TTL
    assert answer.rd == data.name + "." + MEDIAREMOTE_SERVICE


@pytest.mark.asyncio
async def test_service_has_valid_srv_resource(event_loop, udns_server):
    resp, data = await request(event_loop, udns_server, MEDIAREMOTE_SERVICE)

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
    resp, data = await request(event_loop, udns_server, MEDIAREMOTE_SERVICE)

    srv = get_qtype(resp.resources, udns.QTYPE_TXT)
    assert srv.qname == data.name + "." + MEDIAREMOTE_SERVICE
    assert srv.qtype == udns.QTYPE_TXT
    assert srv.qclass == fake_udns.DEFAULT_QCLASS
    assert srv.ttl == fake_udns.DEFAULT_TTL

    rd = srv.rd
    assert len(rd) == len(data.properties)
    for k, v in data.properties.items():
        assert rd[k.encode("ascii")] == v.encode("ascii")
