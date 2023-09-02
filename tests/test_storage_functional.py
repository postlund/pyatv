"""Functional tests for storage.

Tests for top level methods such as scan, pair and connect.
Uses MemoryStorage as storage for simplicity.
"""
import asyncio
from unittest.mock import MagicMock, patch

from deepdiff import DeepDiff
import pytest

from pyatv import connect, pair
from pyatv.const import Protocol
from pyatv.interface import Storage
from pyatv.protocols import ProtocolMethods
from pyatv.storage.file_storage import FileStorage

from tests.fake_udns import airplay_service
from tests.protocols.mock_protocol import mock_protocol

pytestmark = pytest.mark.asyncio

STORAGE_FILENAME = "pyatv.conf"


@pytest.fixture(autouse=True)
def setup_target_device(udns_server) -> None:
    udns_server.add_service(airplay_service("airplay", "aa:bb:cc:dd:ee:ff"))


async def new_storage(
    filename: str, loop: asyncio.AbstractEventLoop, mockfs
) -> Storage:
    storage = FileStorage(filename, loop)
    await storage.load()
    return storage


async def test_scan_inserts_into_storage(event_loop, unicast_scan, mockfs):
    storage1 = await new_storage(STORAGE_FILENAME, event_loop, mockfs)

    # Scan for the device, get settings for it and save everything to storage
    conf = (await unicast_scan(storage=storage1))[0]
    settings1 = await storage1.get_settings(conf)
    await storage1.save()

    # Open a new storage (based on the same file as above) and extract same settings.
    # Compare content to ensure they are exactly the same.
    storage2 = await new_storage(STORAGE_FILENAME, event_loop, mockfs)
    settings2 = await storage2.get_settings(conf)
    assert not DeepDiff(settings2.model_dump(), settings1.model_dump())


async def test_provides_storage_to_pairing_handler(
    event_loop, unicast_scan, session_manager, mockfs
):
    storage = await new_storage(STORAGE_FILENAME, event_loop, mockfs)

    conf = (await unicast_scan(storage=storage))[0]
    settings = await storage.get_settings(conf)

    with mock_protocol(Protocol.AirPlay) as airplay_mock:
        # Calling pair will save Core instance in protocol mock
        await pair(conf, Protocol.AirPlay, event_loop, session=session_manager.session)

        assert airplay_mock.core.settings == settings


async def test_provides_storage_to_connect(
    event_loop, unicast_scan, session_manager, mockfs
):
    storage = await new_storage(STORAGE_FILENAME, event_loop, mockfs)

    conf = (await unicast_scan(storage=storage))[0]
    settings = await storage.get_settings(conf)
    settings.protocols.airplay.credentials = "creds"

    with mock_protocol(Protocol.AirPlay) as airplay_mock:
        await connect(
            conf, event_loop, session=session_manager.session, storage=storage
        )

        # connect will create a copy of the config and load settings in there. Extract
        # the config actually used via Core instance.
        airplay_service = airplay_mock.core.config.get_service(Protocol.AirPlay)
        assert airplay_service.credentials == "creds"
