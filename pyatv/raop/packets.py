"""Packet formats used by RAOP."""
from collections import namedtuple
import struct


def defmsg(name: str, **kwargs):
    """Define a protocol message."""
    fmt: str = ">" + "".join(kwargs.values())
    msg_type = namedtuple(name, kwargs.keys())  # type: ignore

    class _MessageType:
        @staticmethod
        def decode(data: bytes, allow_excessive=False):
            """Decode binary data as message."""
            return msg_type._make(
                struct.unpack(
                    fmt, data if not allow_excessive else data[0 : struct.calcsize(fmt)]
                )
            )

        @staticmethod
        def encode(*args) -> bytes:
            """Encode a message into binary data."""
            return struct.pack(fmt, *args)

        @staticmethod
        def extend(ext_name, **ext_kwargs):
            """Extend a message type with additional fields."""
            fields = {**kwargs, **ext_kwargs}
            return defmsg(ext_name, **fields)

    return _MessageType


RtpHeader = defmsg("RtpHeader", proto="B", type="B", seqno="H")

TimingPacket = RtpHeader.extend(
    "TimingPacket",
    padding="I",
    reftime_sec="I",
    reftime_frac="I",
    recvtime_sec="I",
    recvtime_frac="I",
    sendtime_sec="I",
    sendtime_frac="I",
)

SyncPacket = RtpHeader.extend(
    "AudioPacket",
    now_without_latency="I",
    last_sync_sec="I",
    last_sync_frac="I",
    now="I",
)

# NB: Audio payload is not included here, shall be appended manually
AudioPacketHeader = RtpHeader.extend(
    "AudioPacketHeader",
    timestamp="I",
    ssrc="I",
)

RetransmitReqeust = RtpHeader.extend(
    "RetransmitPacket", lost_seqno="H", lost_packets="H"
)
