from types import SimpleNamespace
import typing
from unittest.mock import Mock, patch

import netifaces
import pytest

import pyatv
from pyatv import conf
from pyatv.support.http import create_session
from pyatv.support.net import unused_port

from tests import fake_udns
from tests.fake_knock import create_knock_server
from tests.utils import stub_sleep, unstub_sleep

#: A type alias for the [multi,uni]cast_scan fixtures.
# There isn't a way to type-hint optional arguments, so instead we leave it unspecified.
Scanner = typing.Callable[..., typing.Awaitable[typing.List[conf.AppleTV]]]


def pytest_configure(config):
    config.addinivalue_line("markers", "use_heartbeat: enable MRP heart beata")


@pytest.fixture(autouse=True)
def stub_netifaces():
    methods = {
        "interfaces": Mock(return_value=["eth0"]),
        "ifaddresses": Mock(
            return_value={
                netifaces.AF_INET: [
                    {
                        "addr": "10.0.10.1",
                        "netmask": "255.255.255.0",
                        "broadcast": "10.0.10.255",
                    },
                    {
                        "addr": "127.0.0.1",
                        "netmask": "255.0.0.0",
                    },
                ]
            }
        ),
    }

    with patch.multiple("netifaces", **methods):
        yield


@pytest.fixture(autouse=True, name="stub_sleep")
def stub_sleep_fixture():
    stub_sleep()
    yield
    unstub_sleep()


# The heartbeat loop uses sleep between each heartbeat, which causes a hogging
# loop in tests since sleep is stubbed. So always stub heartbeats in functional
# tests and rely on unit tests (which can enable heartbeats via the use_heartbeats
# marker in pytest).
@pytest.fixture(autouse=True)
def stub_heartbeat_loop(request):
    if "use_heartbeat" not in request.keywords:

        async def _stub_heartbeat_loop(protocol):
            pass

        with patch("pyatv.mrp.protocol.heartbeat_loop") as mock_heartbeat:
            mock_heartbeat.side_effect = _stub_heartbeat_loop
            yield
    else:
        yield


@pytest.fixture
def session_manager():
    session_manager = create_session()
    yield session_manager
    session_manager.close()


@pytest.fixture
async def knock_server(event_loop):
    servers = []

    async def _add_server():
        server, knock_server = await create_knock_server(unused_port(), event_loop)
        servers.append(server)
        return knock_server

    yield _add_server

    for server in servers:
        server.close()


@pytest.fixture
def stub_knock_server():
    with patch("pyatv.support.knock.knock") as knock:
        info = SimpleNamespace(ports=set(), knock_count=0)

        async def _stub_knock(address, ports, loop):
            info.ports.update(ports)
            info.knock_count += 1

        knock.side_effect = _stub_knock
        yield info


# stub_knock_server is added here to make sure all UDNS tests uses a stubbed
# knock server
@pytest.fixture
async def udns_server(event_loop, stub_knock_server):
    server = fake_udns.FakeUdns(event_loop)
    await server.start()
    yield server
    server.close()


@pytest.fixture(name="multicast_scan")
async def multicast_scan_fixture(event_loop, udns_server):
    async def _scan(timeout=1, identifier=None, protocol=None):
        with fake_udns.stub_multicast(udns_server, event_loop):
            return await pyatv.scan(
                event_loop, identifier=identifier, protocol=protocol, timeout=timeout
            )

    yield _scan


@pytest.fixture(name="unicast_scan")
async def unicast_scan_fixture(event_loop, udns_server):
    async def _scan(timeout=1, identifier=None, protocol=None):
        port = str(udns_server.port)
        with patch.dict("os.environ", {"PYATV_UDNS_PORT": port}):
            return await pyatv.scan(
                event_loop,
                hosts=["127.0.0.1"],
                timeout=timeout,
                identifier=identifier,
                protocol=protocol,
            )

    yield _scan
