"""Fixtures and code shared between MRP tests."""

import asyncio

import pytest

from pyatv.core.protocol import MessageDispatcher
from pyatv.protocols.mrp import protobuf


# This mock is _extremely_ basic, so needs to be adjusted heavily when adding
# new tests
class MrpProtocolMock(MessageDispatcher[int, protobuf.ProtocolMessage]):
    def __init__(self):
        super().__init__()
        self.sent_messages = []
        self.device_info = None

    async def send(self, message):
        self.sent_messages.append(message)

    async def inject(self, message: protobuf.ProtocolMessage) -> None:
        await asyncio.gather(*self.dispatch(message.type, message))


@pytest.fixture(name="protocol_mock")
def protocol_mock_fixture(event_loop):
    yield MrpProtocolMock()
