"""Functional tests pyatv.support.mdns."""

import asyncio
import logging
from ipaddress import IPv4Address
from unittest.mock import MagicMock, patch

import pytest

from pyatv.support import mdns, net
from tests import fake_udns, utils


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
def mdns_debug():
    logger = logging.getLogger("pyatv.support.mdns")
    logger.setLevel(mdns.TRAFFIC_LEVEL)
    yield


@pytest.fixture
async def udns_server(event_loop):
    server = fake_udns.FakeUdns(event_loop, TEST_SERVICES)
    await server.start()
    yield server
    server.close()


@pytest.fixture(autouse=True)
def stub_local_addresses():
    with patch("pyatv.net.get_private_addresses") as mock:
        mock.return_value = [IPv4Address("127.0.0.1")]
        yield


# Requests are normally not sent to localhost, so we need to fake that localhost
# is not s loopback address
@pytest.fixture(autouse=True)
def stub_ip_address():
    with patch("pyatv.support.mdns.ip_address") as mock:
        mock.return_value = mock
        mock.is_loopback = False
        yield


# Hack-ish fixture to make sure multicast does not listen on any global port,
# i.e. 5353 since data from other places can leak into the test
@pytest.fixture(autouse=True)
def redirect_mcast(udns_server):
    real_mcast_socket = net.mcast_socket
    with patch("pyatv.net.mcast_socket") as mock:
        mock.side_effect = lambda addr, port=0: real_mcast_socket(
            addr, port if port == udns_server.port else 0
        )
        yield


# This is a very complex fixture that will hook into the receiver of multicast
# responses and abort the "waiting" period whenever all responses or a certain amount
# of requests have been received. Mainly this is for not slowing down tests.
@pytest.fixture
async def multicast_fastexit(event_loop, monkeypatch, udns_server):
    clients: List[asyncio.Future] = []

    # Interface used to set number of expected responses (1 by default)
    conditions: Dict[str, object] = {"responses": 1, "requests": 0}

    # Checks if either response or request count has been fulfilled
    def _check_cond(protocol: mdns.MulticastDnsSdClientProtocol) -> bool:
        if len(protocol.responses) == conditions["responses"]:
            return False
        if conditions["requests"] == 0:
            return True
        return udns_server.request_count < conditions["responses"]

    def _cast(typ, val):
        if isinstance(val, mdns.MulticastDnsSdClientProtocol):

            async def _poll_responses():
                await utils.until(lambda: not _check_cond(val))
                val.semaphore.release()

            clients.append(asyncio.ensure_future(_poll_responses()))
        return val

    monkeypatch.setattr(mdns, "cast", _cast)

    yield lambda **kwargs: conditions.update(**kwargs)
    await asyncio.gather(*clients)


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
    multicast_fastexit(responses=0, requests=0)

    await mdns.multicast(event_loop, [], "127.0.0.1", udns_server.port)


@pytest.mark.asyncio
async def test_multicast_has_valid_service(event_loop, udns_server, multicast_fastexit):
    multicast_fastexit(responses=1, requests=0)

    resp = await mdns.multicast(
        event_loop, [MEDIAREMOTE_SERVICE], "127.0.0.1", udns_server.port
    )
    assert len(resp) == 1

    first = resp[IPv4Address("127.0.0.1")].services[0]
    assert first.type == MEDIAREMOTE_SERVICE
    assert first.name == SERVICE_NAME
    assert first.port == 1234


@pytest.mark.asyncio
async def test_multicast_end_condition_met(
    event_loop, udns_server, multicast_fastexit, stub_ip_address
):
    multicast_fastexit(responses=4, requests=10)

    actor = MagicMock()

    def _end_cond(response):
        actor(response)
        return True

    resp = await mdns.multicast(
        event_loop,
        [MEDIAREMOTE_SERVICE],
        "127.0.0.1",
        udns_server.port,
        end_condition=_end_cond,
    )
    assert len(resp) == 1
    actor.assert_called_once_with(resp[IPv4Address("127.0.0.1")])


@pytest.mark.asyncio
async def test_multicast_sleeping_device(event_loop, udns_server, multicast_fastexit):
    multicast_fastexit(responses=0, requests=3)
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

    multicast_fastexit(responses=1, requests=0)
    udns_server.services = TEST_SERVICES

    resp = await mdns.multicast(
        event_loop, [MEDIAREMOTE_SERVICE], "127.0.0.1", udns_server.port
    )
    assert len(resp) == 1


@pytest.mark.asyncio
async def test_multicast_deep_sleep(event_loop, udns_server, multicast_fastexit):
    multicast_fastexit(responses=1, requests=0)

    resp = await mdns.multicast(
        event_loop, [MEDIAREMOTE_SERVICE], "127.0.0.1", udns_server.port
    )

    assert not resp[IPv4Address("127.0.0.1")].deep_sleep

    udns_server.sleep_proxy = True
    multicast_fastexit(responses=1, requests=0)

    resp = await mdns.multicast(
        event_loop, [MEDIAREMOTE_SERVICE], "127.0.0.1", udns_server.port
    )

    assert resp[IPv4Address("127.0.0.1")].deep_sleep


@pytest.mark.asyncio
async def test_multicast_device_model(event_loop, udns_server, multicast_fastexit):
    multicast_fastexit(responses=1, requests=0)

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
    multicast_fastexit(responses=1, requests=0)

    resp = await mdns.multicast(
        event_loop, [MEDIAREMOTE_SERVICE], "127.0.0.1", udns_server.port
    )

    assert resp[IPv4Address("127.0.0.1")].model == "dummy"
