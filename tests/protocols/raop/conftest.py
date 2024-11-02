"""Shared test code for RAOP test cases."""

import asyncio
from typing import cast

import pytest
import pytest_asyncio

from pyatv import connect
from pyatv.conf import AppleTV, ManualService
from pyatv.const import Protocol

from tests.fake_device import FakeAppleTV, raop
from tests.fake_device.raop import FakeRaopUseCases


@pytest_asyncio.fixture(name="raop_device")
async def raop_device_fixture():
    fake_atv = FakeAppleTV(asyncio.get_running_loop(), test_mode=False)
    fake_atv.add_service(Protocol.RAOP)
    await fake_atv.start()
    yield fake_atv
    await fake_atv.stop()


@pytest.fixture(name="raop_state")
def raop_state_fixture(raop_device):
    yield raop_device.get_state(Protocol.RAOP)


@pytest.fixture(name="raop_usecase")
def raop_usecase_fixture(raop_device) -> FakeRaopUseCases:
    yield cast(FakeRaopUseCases, raop_device.get_usecase(Protocol.RAOP))


@pytest.fixture(name="raop_conf")
def raop_conf_fixture(raop_device, raop_properties):
    service = ManualService(
        "raop_id", Protocol.RAOP, raop_device.get_port(Protocol.RAOP), raop_properties
    )
    conf = AppleTV("127.0.0.1", "Apple TV")
    conf.add_service(service)
    yield conf


@pytest_asyncio.fixture(name="raop_client")
async def raop_client_fixture(raop_conf):
    client = await connect(raop_conf, loop=asyncio.get_running_loop())
    yield client
    await asyncio.gather(*client.close())
