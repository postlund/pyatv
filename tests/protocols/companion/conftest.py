"""Shared test code for Companiom test cases."""
from typing import cast

import pytest

from pyatv import connect
from pyatv.conf import AppleTV, ManualService
from pyatv.const import Protocol
from pyatv.protocols.companion.server_auth import CLIENT_CREDENTIALS

from tests.fake_device import FakeAppleTV, companion
from tests.fake_device.companion import FakeCompanionUseCases


@pytest.fixture(name="companion_device")
async def companion_device_fixture(event_loop):
    fake_atv = FakeAppleTV(event_loop, test_mode=False)
    fake_atv.add_service(Protocol.Companion)
    await fake_atv.start()
    yield fake_atv
    await fake_atv.stop()


@pytest.fixture(name="companion_state")
async def companion_state_fixture(companion_device):
    yield companion_device.get_state(Protocol.Companion)


@pytest.fixture(name="companion_usecase")
async def companion_usecase_fixture(companion_device) -> FakeCompanionUseCases:
    yield cast(FakeCompanionUseCases, companion_device.get_usecase(Protocol.Companion))


@pytest.fixture(name="companion_conf")
def companion_conf_fixture(companion_device):
    airplay = ManualService("airplayid", Protocol.AirPlay, 0, {})
    service = ManualService(
        None,
        Protocol.Companion,
        companion_device.get_port(Protocol.Companion),
        {},
        credentials=CLIENT_CREDENTIALS,
    )
    conf = AppleTV("127.0.0.1", "Apple TV")
    conf.add_service(service)
    conf.add_service(airplay)
    yield conf


@pytest.fixture(name="companion_client")
async def companion_client_fixture(companion_conf, event_loop):
    yield await connect(companion_conf, loop=event_loop)
