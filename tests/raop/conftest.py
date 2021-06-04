"""Shared test code for RAOP test cases."""
import pytest

from pyatv import connect
from pyatv.conf import AppleTV, RaopService
from pyatv.const import Protocol

from tests.fake_device import FakeAppleTV


@pytest.fixture(name="raop_device")
async def raop_device_fixture(event_loop):
    fake_atv = FakeAppleTV(event_loop, test_mode=False)
    fake_atv.add_service(Protocol.RAOP)
    await fake_atv.start()
    yield fake_atv
    await fake_atv.stop()


@pytest.fixture(name="raop_conf")
def raop_conf_fixture(raop_device):
    service = RaopService(
        "raop_id", port=raop_device.get_port(Protocol.RAOP), properties={"et": "0"}
    )
    conf = AppleTV("127.0.0.1", "Apple TV")
    conf.add_service(service)
    yield conf


@pytest.fixture(name="raop_client")
async def raop_client_fixture(raop_conf, event_loop):
    yield await connect(raop_conf, loop=event_loop)
