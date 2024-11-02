"""Shared test code for Companiom test cases."""

import asyncio
from typing import cast

import pytest
import pytest_asyncio

from pyatv import connect
from pyatv.auth.server_auth import CLIENT_CREDENTIALS
from pyatv.conf import AppleTV, ManualService
from pyatv.const import Protocol

from tests.fake_device import FakeAppleTV
from tests.fake_device.companion import FakeCompanionUseCases


@pytest_asyncio.fixture(name="companion_device")
async def companion_device_fixture():
    fake_atv = FakeAppleTV(asyncio.get_running_loop(), test_mode=False)
    fake_atv.add_service(Protocol.Companion)
    await fake_atv.start()
    yield fake_atv
    await fake_atv.stop()


@pytest.fixture(name="companion_state")
def companion_state_fixture(companion_device):
    yield companion_device.get_state(Protocol.Companion)


@pytest.fixture(name="companion_usecase")
def companion_usecase_fixture(companion_device) -> FakeCompanionUseCases:
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


@pytest_asyncio.fixture(name="companion_client")
async def companion_client_fixture(companion_conf):
    atv = await connect(companion_conf, loop=asyncio.get_running_loop())
    yield atv
    await asyncio.gather(*atv.close())
