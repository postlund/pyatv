"""Regression tests for Companion transaction ID OPACK encoding.

A positive XID must be serialized with enough bytes to remain positive when
interpreted as a signed integer by tvOS. Ordinary unsigned OPACK properties
are intentionally unaffected.
"""

from types import SimpleNamespace

import pytest

from pyatv.protocols.companion.connection import FrameType
from pyatv.protocols.companion.protocol import (
    CompanionProtocol,
    MessageType,
    _opack_xid,
)
from pyatv.support import opack


@pytest.mark.parametrize(
    "xid,encoded",
    [
        (0x27, b"\x2f"),
        (0x7F, b"\x30\x7f"),
        (0x80, b"\x31\x80\x00"),
        (0x7FFF, b"\x31\xff\x7f"),
        (0x8000, b"\x32\x00\x80\x00\x00"),
        (0xFF7F, b"\x32\x7f\xff\x00\x00"),
        (0xFF80, b"\x32\x80\xff\x00\x00"),
        (0xFFFE, b"\x32\xfe\xff\x00\x00"),
        (0xFFFF, b"\x32\xff\xff\x00\x00"),
        (0x10000, b"\x32\x00\x00\x01\x00"),
        (0x7FFFFFFF, b"\x32\xff\xff\xff\x7f"),
        (0x80000000, b"\x33\x00\x00\x00\x80\x00\x00\x00\x00"),
    ],
)
def test_companion_xid_uses_signed_safe_width(xid: int, encoded: bytes) -> None:
    assert opack.pack(_opack_xid(xid)) == encoded
    assert opack.unpack(encoded) == (xid, b"")


@pytest.mark.parametrize(
    "value,size,encoded",
    [
        (128, 2, b"\x31\x80\x00"),
        (32768, 4, b"\x32\x00\x80\x00\x00"),
        (65408, 4, b"\x32\x80\xff\x00\x00"),
        (65535, 4, b"\x32\xff\xff\x00\x00"),
        (2147483648, 8, b"\x33\x00\x00\x00\x80\x00\x00\x00\x00"),
    ],
)
def test_public_opack_sized_int(value: int, size: int, encoded: bytes) -> None:
    """Verify explicit-width OPACK encoding via the public API."""
    assert opack.pack(opack.sized_int(value, size)) == encoded


def test_companion_xid_rejects_out_of_range_values() -> None:
    with pytest.raises(ValueError):
        _opack_xid(-1)
    with pytest.raises(OverflowError):
        _opack_xid(1 << 63)


@pytest.mark.asyncio
@pytest.mark.parametrize("xid", [0x7F, 0x80, 0xFF7F, 0xFF80, 0xFFFF, 0x10000])
async def test_exchange_opack_sends_correctly_encoded_xid(xid: int) -> None:
    async def exchange(
        frame_type: FrameType,
        data: dict[str, object],
        identifier: int,
        timeout: float,
    ) -> dict[str, object]:
        assert frame_type == FrameType.E_OPACK
        assert identifier == xid
        decoded, remainder = opack.unpack(opack.pack(data))
        assert remainder == b""
        assert decoded["_x"] == xid
        return {"_t": MessageType.Response.value, "_x": xid}

    protocol = SimpleNamespace(_xid=xid, _exchange_generic_opack=exchange)
    result = await CompanionProtocol.exchange_opack(
        protocol, FrameType.E_OPACK, {"_i": "FetchAttentionState"}
    )
    assert result["_x"] == xid
    assert protocol._xid == xid + 1


@pytest.mark.parametrize("xid", [0x80, 0xFF80, 0xFFFF, 0x10000])
def test_send_opack_uses_correctly_encoded_xid(xid: int) -> None:
    frames: list[tuple[FrameType, bytes]] = []

    def send(frame_type: FrameType, payload: bytes) -> None:
        frames.append((frame_type, payload))

    connection = SimpleNamespace(send=send)
    protocol = SimpleNamespace(_xid=xid, connection=connection)

    CompanionProtocol.send_opack(protocol, FrameType.E_OPACK, {"_i": "test"})

    assert protocol._xid == xid + 1
    assert len(frames) == 1
    data, remainder = opack.unpack(frames[0][1])
    assert remainder == b""
    assert data["_x"] == xid


def test_out_of_order_response_ids_remain_distinct() -> None:
    """Responses with different XIDs never alias an unrelated pending request."""
    requests = [0x80, 0xFF7F, 0xFF80, 0xFFFF, 0x10000]

    class Receiver:
        def __init__(self) -> None:
            self.value: dict[str, object] | None = None

        def set(self, value: dict[str, object]) -> None:
            self.value = value

    receivers = {xid: Receiver() for xid in requests}
    protocol = SimpleNamespace(_queues=dict(receivers))

    for xid in reversed(requests):
        response = {"_t": MessageType.Response.value, "_x": _opack_xid(xid)}
        decoded, remainder = opack.unpack(opack.pack(response))
        assert remainder == b""
        CompanionProtocol._handle_opack(protocol, FrameType.E_OPACK, decoded)

    assert not protocol._queues
    for xid in requests:
        assert receivers[xid].value is not None
        assert receivers[xid].value["_x"] == xid
