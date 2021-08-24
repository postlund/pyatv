"""Generic utility for encoding and decoding binary packets."""
from collections import namedtuple
import struct


def defpacket(name: str, **kwargs):
    """Define a protocol packet."""
    fmt: str = ">" + "".join(kwargs.values())
    msg_type = namedtuple(name, kwargs.keys())  # type: ignore

    class _MessageType:
        length = struct.calcsize(fmt)

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
            return defpacket(ext_name, **fields)

    return _MessageType
