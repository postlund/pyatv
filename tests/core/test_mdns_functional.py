"""Functional tests pyatv.core.mdns."""

import asyncio
from ipaddress import IPv4Address
import logging
import typing
from unittest.mock import MagicMock, patch

import pytest
import pytest_asyncio

from pyatv.core import mdns
from pyatv.support import net

from tests import fake_udns, utils

SERVICE_NAME = "Kitchen"
MEDIAREMOTE_SERVICE = "_mediaremotetv._tcp.local"
DEVICE_INFO_SERVICE = "_device-info._tcp._local"

SERVICES_PER_REQUEST = 3

TEST_SERVICES = dict(
    [
        fake_udns.mrp_service(
            SERVICE_NAME, SERVICE_NAME, "mrp_id", addresses=["127.0.0.1"], port=1234
        ),
    ]
)


def gen_test_services(count: int) -> typing.List[str]:
    return [f"srv{i}._tcp.local" for i in range(count)]


pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
def mdns_debug():
    logger = logging.getLogger("pyatv.core.mdns")
    logger.setLevel(mdns.TRAFFIC_LEVEL)
    yield


@pytest.fixture(autouse=True)
def stub_local_addresses():
    with patch("pyatv.support.net.get_private_addresses") as mock:
        mock.return_value = [IPv4Address("127.0.0.1")]
        yield


# Requests are normally not sent to localhost, so we need to fake that localhost
# is not s loopback address
@pytest.fixture(autouse=True)
def stub_ip_address():
    with patch("pyatv.core.mdns.ip_address") as mock:
        mock.return_value = mock
        mock.is_loopback = False
        yield


# Hack-ish fixture to make sure multicast does not listen on any global port,
# i.e. 5353 since data from other places can leak into the test
@pytest_asyncio.fixture(autouse=True)
def redirect_mcast(udns_server):
    udns_server.services = TEST_SERVICES
    real_mcast_socket = net.mcast_socket
    with patch("pyatv.support.net.mcast_socket") as mock:
        mock.side_effect = lambda addr, port=0: real_mcast_socket(
            addr, port if port == udns_server.port else 0
        )
        yield


# This is a very complex fixture that will hook into the receiver of multicast
# responses and abort the "waiting" period whenever all responses or a certain amount
# of requests have been received. Mainly this is for not slowing down tests.
@pytest_asyncio.fixture
async def multicast_fastexit(monkeypatch, udns_server):
    clients: typing.List[asyncio.Future] = []

    # Interface used to set number of expected responses (1 by default)
    conditions: typing.Dict[str, object] = {"responses": 1, "requests": 0}

    # Checks if either response or request count has been fulfilled
    def _check_cond(protocol: mdns.MulticastDnsSdClientProtocol) -> bool:
        if len(protocol.query_responses) == conditions["responses"]:
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

    monkeypatch.setattr(typing, "cast", _cast)

    yield lambda **kwargs: conditions.update(**kwargs)
    await asyncio.gather(*clients)


async def unicast(udns_server, service_names, timeout=1):
    return (
        await mdns.unicast(
            asyncio.get_running_loop(),
            "127.0.0.1",
            service_names,
            port=udns_server.port,
            timeout=timeout,
        ),
        TEST_SERVICES.get(service_names[0]),
    )


@pytest.mark.asyncio
async def test_unicast_has_valid_service(udns_server):
    resp, service = await unicast(udns_server, [MEDIAREMOTE_SERVICE])
    assert len(resp.services) == 1
    assert resp.services[0].type == MEDIAREMOTE_SERVICE
    assert resp.services[0].name == service.name
    assert resp.services[0].port == service.port


@pytest.mark.parametrize(
    "service_count,expected_requests",
    [
        (1, 1),
        (SERVICES_PER_REQUEST, 1),
        (SERVICES_PER_REQUEST + 1, 2),
        (2 * SERVICES_PER_REQUEST + 1, 3),
    ],
)
async def test_unicast_multiple_requests(service_count, expected_requests, udns_server):
    resp, _ = await unicast(udns_server, gen_test_services(service_count))
    assert udns_server.request_count == expected_requests


async def test_unicast_resend_if_no_response(udns_server):
    udns_server.skip_count = 2
    resp, service = await unicast(udns_server, [MEDIAREMOTE_SERVICE], 3)
    assert len(resp.services) == 1
    assert resp.services[0].type == MEDIAREMOTE_SERVICE
    assert resp.services[0].name == service.name
    assert resp.services[0].port == service.port


async def test_unicast_specific_service(udns_server):
    resp, _ = await unicast(udns_server, [SERVICE_NAME + "." + MEDIAREMOTE_SERVICE])
    assert len(resp.services) == 1

    service = TEST_SERVICES.get(MEDIAREMOTE_SERVICE)
    assert resp.services[0].type == MEDIAREMOTE_SERVICE
    assert resp.services[0].name == service.name
    assert resp.services[0].port == service.port


async def test_unicast_includes_sleep_proxy_service(udns_server):
    udns_server.services = {
        "_test._tcp.local": fake_udns.FakeDnsService(
            name="test", addresses=["127.0.0.1"], port=1234, properties={}, model=None
        ),
        "_sleep-proxy._udp.local": fake_udns.FakeDnsService(
            name="sleepy", addresses=["127.0.0.1"], port=5678, properties={}, model=None
        ),
    }

    # _sleep-proxy._udp.local should be requested implicitly in unicast for
    # any service
    resp, _ = await unicast(udns_server, ["_test._tcp.local"])
    assert len(resp.services) == 2

    proxy = [
        service
        for service in resp.services
        if service.type == "_sleep-proxy._udp.local"
    ][0]
    assert proxy.name == "sleepy"
    assert proxy.port == 5678


async def test_multicast_no_response(udns_server, multicast_fastexit):
    multicast_fastexit(responses=0, requests=0)

    await mdns.multicast(asyncio.get_running_loop(), [], "127.0.0.1", udns_server.port)


async def test_multicast_has_valid_service(udns_server, multicast_fastexit):
    multicast_fastexit(responses=1, requests=0)

    resp = await mdns.multicast(
        asyncio.get_running_loop(), [MEDIAREMOTE_SERVICE], "127.0.0.1", udns_server.port
    )
    assert len(resp) == 1

    first = resp[0].services[0]
    assert first.type == MEDIAREMOTE_SERVICE
    assert first.name == SERVICE_NAME
    assert first.port == 1234


async def test_multicast_end_condition_met(
    udns_server, multicast_fastexit, stub_ip_address
):
    multicast_fastexit(responses=1, requests=10)

    actor = MagicMock()

    def _end_cond(response):
        actor(response)
        return True

    resp = await mdns.multicast(
        asyncio.get_running_loop(),
        [MEDIAREMOTE_SERVICE],
        "127.0.0.1",
        udns_server.port,
        end_condition=_end_cond,
    )
    assert len(resp) == 1
    actor.assert_called_once_with(resp[0])


async def test_multicast_sleeping_device(udns_server, multicast_fastexit):
    multicast_fastexit(responses=0, requests=3)
    udns_server.sleep_proxy = True

    udns_server.services = {
        MEDIAREMOTE_SERVICE: fake_udns.FakeDnsService(
            name=SERVICE_NAME, addresses=[], port=0, properties={}, model=None
        ),
    }

    resp = await mdns.multicast(
        asyncio.get_running_loop(), [MEDIAREMOTE_SERVICE], "127.0.0.1", udns_server.port
    )
    assert len(resp) == 0

    multicast_fastexit(responses=1, requests=0)
    udns_server.services = TEST_SERVICES

    resp = await mdns.multicast(
        asyncio.get_running_loop(), [MEDIAREMOTE_SERVICE], "127.0.0.1", udns_server.port
    )
    assert len(resp) == 1


async def test_multicast_deep_sleep(udns_server, multicast_fastexit):
    multicast_fastexit(responses=1, requests=0)

    resp = await mdns.multicast(
        asyncio.get_running_loop(), [MEDIAREMOTE_SERVICE], "127.0.0.1", udns_server.port
    )

    assert not resp[0].deep_sleep

    udns_server.sleep_proxy = True
    multicast_fastexit(responses=1, requests=0)

    resp = await mdns.multicast(
        asyncio.get_running_loop(), [MEDIAREMOTE_SERVICE], "127.0.0.1", udns_server.port
    )

    assert resp[0].deep_sleep


async def test_multicast_device_model(udns_server, multicast_fastexit):
    multicast_fastexit(responses=1, requests=0)

    resp = await mdns.multicast(
        asyncio.get_running_loop(), [MEDIAREMOTE_SERVICE], "127.0.0.1", udns_server.port
    )

    assert not resp[0].model

    udns_server.services = {
        MEDIAREMOTE_SERVICE: fake_udns.FakeDnsService(
            name=SERVICE_NAME,
            addresses=["127.0.0.1"],
            port=1234,
            properties={},
            model="dummy",
        ),
    }
    multicast_fastexit(responses=1, requests=0)

    resp = await mdns.multicast(
        asyncio.get_running_loop(), [MEDIAREMOTE_SERVICE], "127.0.0.1", udns_server.port
    )

    assert resp[0].model == "dummy"
