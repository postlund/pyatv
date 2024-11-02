"""Shared test code for AirPlay test cases."""

import asyncio

import pytest
import pytest_asyncio

from pyatv.conf import AppleTV, ManualService
from pyatv.const import Protocol
from pyatv.support.http import http_connect

from tests.fake_device import FakeAppleTV


@pytest_asyncio.fixture(name="airplay_device")
async def airplay_device_fixture():
    fake_atv = FakeAppleTV(asyncio.get_running_loop(), test_mode=False)
    fake_atv.add_service(Protocol.AirPlay)
    await fake_atv.start()
    yield fake_atv
    await fake_atv.stop()


@pytest_asyncio.fixture(name="client_connection")
async def client_connection_fixture(airplay_device):
    yield await http_connect("127.0.0.1", airplay_device.get_port(Protocol.AirPlay))


@pytest.fixture(name="airplay_usecase")
def airplay_usecase_fixture(airplay_device):
    yield airplay_device.get_usecase(Protocol.AirPlay)


@pytest.fixture(name="airplay_state")
def airplay_state_fixture(airplay_device):
    yield airplay_device.get_state(Protocol.AirPlay)


@pytest.fixture(name="airplay_properties")
def airplay_properties_fixture():
    yield {}


@pytest.fixture(name="airplay_conf")
def airplay_conf_fixture(airplay_device, airplay_properties):
    service = ManualService(
        "airplay_id",
        Protocol.AirPlay,
        airplay_device.get_port(Protocol.AirPlay),
        airplay_properties,
    )
    conf = AppleTV("127.0.0.1", "Apple TV")
    conf.add_service(service)
    yield conf
