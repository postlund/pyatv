"""Shared test code for AirPlay test cases."""
import pytest

from pyatv.conf import AppleTV, ManualService
from pyatv.const import Protocol
from pyatv.support.http import http_connect

from tests.fake_device import FakeAppleTV


@pytest.fixture(name="airplay_device")
async def airplay_device_fixture(event_loop):
    fake_atv = FakeAppleTV(event_loop, test_mode=False)
    fake_atv.add_service(Protocol.AirPlay)
    await fake_atv.start()
    yield fake_atv
    await fake_atv.stop()


@pytest.fixture(name="client_connection")
async def client_connection_fixture(airplay_device, event_loop):
    yield await http_connect("127.0.0.1", airplay_device.get_port(Protocol.AirPlay))


@pytest.fixture(name="airplay_usecase")
def airplay_usecase_fixture(airplay_device):
    yield airplay_device.get_usecase(Protocol.AirPlay)


@pytest.fixture(name="airplay_state")
def airplay_state_fixture(airplay_device):
    yield airplay_device.get_state(Protocol.AirPlay)


@pytest.fixture(name="airplay_conf")
def airplay_conf_fixture(airplay_device):
    service = ManualService(
        "airplay_id", Protocol.AirPlay, airplay_device.get_port(Protocol.AirPlay), {}
    )
    conf = AppleTV("127.0.0.1", "Apple TV")
    conf.add_service(service)
    yield conf
