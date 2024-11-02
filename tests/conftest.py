import asyncio
import builtins
import logging
from os import path
from types import SimpleNamespace
import typing
from unittest.mock import Mock, patch

from ifaddr import IP, Adapter
import pytest
import pytest_asyncio
from pytest_httpserver import HTTPServer

import pyatv
from pyatv.auth.hap_pairing import parse_credentials
from pyatv.const import Protocol
from pyatv.core import CoreStateDispatcher, ProtocolStateDispatcher
from pyatv.interface import BaseConfig
from pyatv.support.http import create_session
from pyatv.support.net import unused_port

from tests import fake_udns
from tests.fake_device.airplay import DEVICE_CREDENTIALS
from tests.fake_knock import create_knock_server
from tests.utils import data_root, stub_sleep, unstub_sleep

_LOGGER = logging.getLogger(__name__)

#: A type alias for the [multi,uni]cast_scan fixtures.
# There isn't a way to type-hint optional arguments, so instead we leave it unspecified.
Scanner = typing.Callable[..., typing.Awaitable[typing.List[BaseConfig]]]


def pytest_configure(config):
    config.addinivalue_line("markers", "use_heartbeat: enable MRP heart beata")


@pytest.fixture(autouse=True)
def stub_ifaddr():
    methods = {
        "get_adapters": Mock(
            return_value=[
                Adapter("eth0", "eth0", [IP("10.0.10.1", 24, "eth0")]),
                Adapter("lo", "lo", [IP("127.0.0.1", 8, "lo")]),
            ]
        )
    }
    with patch.multiple("pyatv.support.net", **methods):
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

        async def _stub_heartbeat_loop(*args, **kwargs):
            _LOGGER.debug("Using stub for heartbeat")

        with patch("pyatv.protocols.mrp.protocol.heartbeater") as mock_heartbeat:
            mock_heartbeat.side_effect = _stub_heartbeat_loop
            yield
    else:
        yield


@pytest_asyncio.fixture
async def session_manager():
    session_manager = await create_session()
    yield session_manager
    await session_manager.close()


@pytest_asyncio.fixture
async def knock_server():
    servers = []

    async def _add_server():
        server, knock_server = await create_knock_server(
            unused_port(), asyncio.get_running_loop()
        )
        servers.append(server)
        return knock_server

    yield _add_server

    for server in servers:
        server.close()


@pytest_asyncio.fixture
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
@pytest_asyncio.fixture
async def udns_server(stub_knock_server):
    server = fake_udns.FakeUdns(asyncio.get_running_loop())
    await server.start()
    yield server
    server.close()


@pytest_asyncio.fixture(name="multicast_scan")
async def multicast_scan_fixture(udns_server):
    async def _scan(timeout=1, identifier=None, protocol=None):
        with fake_udns.stub_multicast(udns_server, asyncio.get_running_loop()):
            return await pyatv.scan(
                asyncio.get_running_loop(),
                identifier=identifier,
                protocol=protocol,
                timeout=timeout,
            )

    yield _scan


@pytest_asyncio.fixture(name="unicast_scan")
async def unicast_scan_fixture(udns_server):
    async def _scan(timeout=1, identifier=None, protocol=None, storage=None):
        port = str(udns_server.port)
        with patch.dict("os.environ", {"PYATV_UDNS_PORT": port}):
            return await pyatv.scan(
                asyncio.get_running_loop(),
                hosts=["127.0.0.1"],
                timeout=timeout,
                identifier=identifier,
                protocol=protocol,
                storage=storage,
            )

    yield _scan


# This fixture stubs the normally random credential generation of legacy credentials
# in AirPlay, so the hardcoded device credentials can be used. It should ultimately
# be placed somewhere more close to the AirPlay code, but since some tests requiring
# this fixture haven't been converted to pytest yet (and cannot explicitly use
# fixtures), it will live here for now.
@pytest.fixture(name="airplay_creds", autouse=True)
def airplay_creds_fixture():
    with patch("pyatv.protocols.airplay.auth.new_credentials") as new_credentials:
        new_credentials.return_value = parse_credentials(DEVICE_CREDENTIALS)
        yield


@pytest.fixture(name="core_dispatcher")
def core_dispatcher():
    yield CoreStateDispatcher()


@pytest.fixture(name="mrp_state_dispatcher")
def mrp_state_dispatcher_fixture(core_dispatcher):
    yield ProtocolStateDispatcher(Protocol.MRP, core_dispatcher)


@pytest.fixture(name="dmap_state_dispatcher")
def dmap_state_dispatcher_fixture(core_dispatcher):
    yield ProtocolStateDispatcher(Protocol.DMAP, core_dispatcher)


@pytest.fixture(name="companion_state_dispatcher")
def companion_state_dispatcher_fixture(core_dispatcher):
    yield ProtocolStateDispatcher(Protocol.Companion, core_dispatcher)


# "files" is a list of filenames from tests/data directory that will be served
# as binary files from the HTTP server
@pytest.fixture(name="data_webserver")
def data_webserver_fixture(httpserver: HTTPServer, files: typing.Sequence[str]):
    root_dir = data_root()
    for file in files:
        with open(path.join(root_dir, file), "rb") as _fh:
            httpserver.expect_request("/" + file).respond_with_data(_fh.read())
    yield httpserver.url_for("/")


@pytest.fixture(name="mockfs")
def mockfs_fixture(fs):
    yield fs
