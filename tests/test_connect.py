"""Unit tests for pyatv.connect."""

import asyncio
from ipaddress import IPv4Address

import pytest

from pyatv import connect, exceptions
from pyatv.conf import AppleTV, ManualService
from pyatv.const import Protocol

from tests.protocols.mock_protocol import mock_protocol

pytestmark = pytest.mark.asyncio


async def test_connect_failure_awaits_protocol_close(session_manager):
    conf = AppleTV(IPv4Address("127.0.0.1"), "Test")
    conf.add_service(ManualService("id", Protocol.AirPlay, 7000, {}))
    close_done = asyncio.Event()

    async def _close_task() -> None:
        close_done.set()

    with mock_protocol(Protocol.AirPlay) as airplay_mock:
        airplay_mock.setup_mock.connect.side_effect = exceptions.ConnectionFailedError
        airplay_mock.setup_mock.close.side_effect = lambda: {
            asyncio.ensure_future(_close_task())
        }

        with pytest.raises(exceptions.ConnectionFailedError):
            await connect(
                conf, asyncio.get_running_loop(), session=session_manager.session
            )

    airplay_mock.setup_mock.close.assert_called_once()
    assert close_done.is_set()
