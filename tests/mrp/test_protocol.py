"""Unittests for pyatv.mrp.protocol."""
import pytest

from pyatv.conf import MrpService
from pyatv.const import Protocol
from pyatv.mrp.connection import MrpConnection
from pyatv.mrp.protocol import MrpProtocol
from pyatv.mrp.srp import SRPAuthHandler

from tests.utils import until, stub_sleep
from tests.fake_device import FakeAppleTV


@pytest.fixture
async def mrp_atv(event_loop):
    atv = FakeAppleTV(event_loop)
    atv.add_service(Protocol.MRP)
    await atv.start()
    yield atv
    await atv.stop()


@pytest.fixture
async def mrp_protocol(event_loop, mrp_atv):
    port = mrp_atv.get_port(Protocol.MRP)
    service = MrpService("mrp_id", port)
    connection = MrpConnection("127.0.0.1", port, event_loop)
    protocol = MrpProtocol(connection, SRPAuthHandler(), service)
    yield protocol
    protocol.stop()


@pytest.mark.asyncio
@pytest.mark.use_heartbeat
async def test_heartbeat_loop(mrp_atv, mrp_protocol):
    await mrp_protocol.start()

    mrp_state = mrp_atv.get_state(Protocol.MRP)
    await until(lambda: mrp_state.heartbeat_count >= 3)
