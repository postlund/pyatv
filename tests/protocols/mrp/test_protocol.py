"""Unittests for pyatv.protocols.mrp.protocol."""

import asyncio
from unittest.mock import MagicMock

import pytest
import pytest_asyncio

from pyatv.auth.hap_srp import SRPAuthHandler
from pyatv.conf import ManualService
from pyatv.const import Protocol
from pyatv import exceptions
from pyatv.protocols.mrp import messages, protobuf
from pyatv.protocols.mrp.connection import AbstractMrpConnection, MrpConnection
from pyatv.protocols.mrp.protocol import (
    HEARTBEAT_INTERVAL,
    HEARTBEAT_RETRIES,
    ProtocolState,
    MrpProtocol,
    heartbeat_loop,
)
from pyatv.settings import InfoSettings

from tests.fake_device import FakeAppleTV
from tests.utils import total_sleep_time, until


class DummyConnection(AbstractMrpConnection):
    """Minimal MRP connection used for protocol unit tests."""

    def __init__(self, connected: bool = True):
        super().__init__()
        self._connected = connected
        self.sent = []
        self.listener = None

    async def connect(self) -> None:  # pragma: no cover - not used in tests
        self._connected = True

    def enable_encryption(self, output_key: bytes, input_key: bytes) -> None:
        return

    @property
    def connected(self) -> bool:
        return self._connected

    def close(self) -> None:
        self._connected = False

    def send(self, message: protobuf.ProtocolMessage) -> None:
        if not self._connected:
            raise exceptions.ConnectionLostError(
                "connection is closed; reconnect required"
            )
        self.sent.append(message)


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


@pytest.mark.asyncio
async def test_send_and_receive_fire_and_forget():
    connection = DummyConnection()
    service = ManualService("mrp_id", Protocol.MRP, 0, {})
    protocol = MrpProtocol(connection, SRPAuthHandler(), service, InfoSettings())
    protocol._state = ProtocolState.CONNECTED

    message = messages.create(protobuf.GENERIC_MESSAGE)
    result = await protocol.send_and_receive(
        message, wait_for_response=False, timeout=1
    )

    assert result is None
    assert connection.sent == [message]


@pytest.mark.asyncio
async def test_send_raises_when_connection_closed():
    connection = DummyConnection(connected=False)
    service = ManualService("mrp_id", Protocol.MRP, 0, {})
    protocol = MrpProtocol(connection, SRPAuthHandler(), service, InfoSettings())
    protocol._state = ProtocolState.CONNECTED

    with pytest.raises(exceptions.ConnectionLostError):
        await protocol.send(messages.create(protobuf.GENERIC_MESSAGE))
