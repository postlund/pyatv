"""Unittests for pyatv.protocols.mrp.protocol."""

import asyncio
from unittest.mock import MagicMock

import pytest
import pytest_asyncio

from pyatv.auth.hap_srp import SRPAuthHandler
from pyatv.conf import ManualService
from pyatv.const import Protocol
from pyatv.protocols.mrp.connection import MrpConnection
from pyatv.protocols.mrp.protocol import (
    HEARTBEAT_INTERVAL,
    HEARTBEAT_RETRIES,
    MrpProtocol,
    heartbeat_loop,
)
from pyatv.settings import InfoSettings

from tests.fake_device import FakeAppleTV
from tests.utils import total_sleep_time, until


@pytest_asyncio.fixture
async def mrp_atv():
    atv = FakeAppleTV(asyncio.get_running_loop())
    atv.add_service(Protocol.MRP)
    await atv.start()
    yield atv
    await atv.stop()


@pytest_asyncio.fixture
async def mrp_protocol(mrp_atv):
    port = mrp_atv.get_port(Protocol.MRP)
    service = ManualService("mrp_id", Protocol.MRP, port, {})
    connection = MrpConnection("127.0.0.1", port, asyncio.get_running_loop())
    protocol = MrpProtocol(connection, SRPAuthHandler(), service, InfoSettings())
    yield protocol
    protocol.stop()


@pytest.mark.asyncio
@pytest.mark.use_heartbeat
async def test_heartbeat_loop(mrp_atv, mrp_protocol):
    await mrp_protocol.start()
    mrp_protocol.enable_heartbeat()

    mrp_state = mrp_atv.get_state(Protocol.MRP)
    await until(lambda: mrp_state.heartbeat_count >= 3)


@pytest.mark.asyncio
async def test_heartbeat_fail_closes_connection(stub_sleep):
    protocol = MagicMock()
    protocol.send_and_receive.side_effect = Exception()

    await heartbeat_loop(protocol)
    assert protocol.send_and_receive.call_count == 1 + HEARTBEAT_RETRIES
    assert total_sleep_time() == HEARTBEAT_INTERVAL

    protocol.connection.close.assert_called_once()
