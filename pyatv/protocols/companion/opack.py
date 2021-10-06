"""Support for the OPACK serialization format.

Notes:
 * Absolute time (0x06) is not implemented (can unpack as integer, not pack)
 * Likely other cases missing
"""
from datetime import datetime

# pylint: disable=too-many-branches,too-many-return-statements,too-many-statements
import struct
from typing import NamedTuple, Tuple
from uuid import UUID


class UID(NamedTuple):
    """Type for UID encoded data.

    Either 1, 2, 3 or 4 bytes (bit endian).
    """

    value: int


def pack(data: object) -> bytes:
    """Pack data structure with OPACK and return bytes."""
    return _pack(data, [])


def _pack(data, object_list):
    packed_bytes = None
    if data is None:
        packed_bytes = b"\x04"
    elif isinstance(data, bool):
        packed_bytes = bytes([1 if data else 2])
    elif isinstance(data, UUID):
        packed_bytes = b"\x05" + data.bytes
    elif isinstance(data, datetime):
        raise NotImplementedError("absolute time")
    elif isinstance(data, int):
        if data < 0x28:
            packed_bytes = bytes([data + 8])
        elif data <= 0xFF:
            packed_bytes = bytes([0x30]) + data.to_bytes(1, byteorder="little")
        elif data <= 0xFFFF:
            packed_bytes = bytes([0x31]) + data.to_bytes(2, byteorder="little")
        elif data <= 0xFFFFFFFF:
            packed_bytes = bytes([0x32]) + data.to_bytes(4, byteorder="little")
        elif data <= 0xFFFFFFFFFFFFFFFF:
            packed_bytes = bytes([0x33]) + data.to_bytes(8, byteorder="little")
    elif isinstance(data, float):
        packed_bytes = b"\x36" + struct.pack("<d", data)
    elif isinstance(data, str):
        encoded = data.encode("utf-8")
        if len(encoded) <= 0x20:
            packed_bytes = bytes([0x40 + len(encoded)]) + encoded
        elif len(encoded) <= 0xFF:
            packed_bytes = (
                bytes([0x61]) + len(encoded).to_bytes(1, byteorder="little") + encoded
            )
        elif len(encoded) <= 0xFFFF:
            packed_bytes = (
                bytes([0x62]) + len(encoded).to_bytes(2, byteorder="little") + encoded
            )
        elif len(encoded) <= 0xFFFFFF:
            packed_bytes = (
                bytes([0x63]) + len(encoded).to_bytes(3, byteorder="little") + encoded
            )
        elif len(encoded) <= 0xFFFFFFFF:
            packed_bytes = (
                bytes([0x64]) + len(encoded).to_bytes(4, byteorder="little") + encoded
            )
    elif isinstance(data, bytes):
        if len(data) <= 0x20:
            packed_bytes = bytes([0x70 + len(data)]) + data
        elif len(data) <= 0xFF:
            packed_bytes = (
                bytes([0x91]) + len(data).to_bytes(1, byteorder="little") + data
            )
        elif len(data) <= 0xFFFF:
            packed_bytes = (
                bytes([0x92]) + len(data).to_bytes(2, byteorder="little") + data
            )
        elif len(data) <= 0xFFFFFF:
            packed_bytes = (
                bytes([0x93]) + len(data).to_bytes(3, byteorder="little") + data
            )
        elif len(data) <= 0xFFFFFFFF:
            packed_bytes = (
                bytes([0x94]) + len(data).to_bytes(4, byteorder="little") + data
            )
    elif isinstance(data, list):
        packed_bytes = bytes([0xD0 + min(len(data), 0xF)]) + b"".join(
            _pack(x, object_list) for x in data
        )
        if len(data) >= 0xF:
            packed_bytes += b"\x03"
    elif isinstance(data, dict):
        packed_bytes = bytes([0xE0 + min(len(data), 0xF)]) + b"".join(
            _pack(k, object_list) + _pack(v, object_list) for k, v in data.items()
        )
        if len(data) >= 0xF:
            packed_bytes += b"\x03"
    elif isinstance(data, UID):
        if data.value <= 0xFF:
            packed_bytes = bytes([0xC1]) + data.value.to_bytes(1, byteorder="big")
        elif data.value <= 0xFFFF:
            packed_bytes = bytes([0xC2]) + data.value.to_bytes(2, byteorder="big")
        elif data.value <= 0xFFFFFF:
            packed_bytes = bytes([0xC3]) + data.value.to_bytes(3, byteorder="big")
        elif data.value <= 0xFFFFFFFF:
            packed_bytes = bytes([0xC4]) + data.value.to_bytes(4, byteorder="big")
    else:
        raise TypeError(str(type(data)))

    # Re-use if in object list, otherwise add it to list
    if packed_bytes in object_list:
        packed_bytes = bytes([0xA0 + object_list.index(packed_bytes)])
    elif len(packed_bytes) > 1:
        object_list.append(packed_bytes)

    return packed_bytes


def unpack(data: bytes) -> Tuple[object, bytes]:
    """Unpack raw OPACK data into python objects."""
    return _unpack(data, [])


def _unpack(data, object_list):
    value = None
    remaining = None
    add_to_object_list = True
    if data[0] == 0x01:
        value, remaining = True, data[1:]
        add_to_object_list = False
    elif data[0] == 0x02:
        value, remaining = False, data[1:]
        add_to_object_list = False
    elif data[0] == 0x04:
        value, remaining = None, data[1:]
        add_to_object_list = False
    elif data[0] == 0x05:
        value = UUID(bytes=data[1:17])
        remaining = data[17:]
    elif data[0] == 0x06:
        # TODO: Dummy implementation: only parse as integer
        value, remaining = int.from_bytes(data[1:9], byteorder="little"), data[9:]
    elif 0x08 <= data[0] <= 0x2F:
        value, remaining = data[0] - 8, data[1:]
        add_to_object_list = False
    elif data[0] == 0x35:
        value, remaining = struct.unpack("<f", data[1:5])[0], data[5:]
    elif data[0] == 0x36:
        value, remaining = struct.unpack("<d", data[1:9])[0], data[9:]
    elif (data[0] & 0xF0) == 0x30:
        noof_bytes = 2 ** (data[0] & 0xF)
        value, remaining = (
            int.from_bytes(data[1 : 1 + noof_bytes], byteorder="little"),
            data[1 + noof_bytes :],
        )
    elif 0x40 <= data[0] <= 0x60:
        length = data[0] - 0x40
        value, remaining = data[1 : 1 + length].decode("utf-8"), data[1 + length :]
    elif 0x60 < data[0] <= 0x64:
        noof_bytes = data[0] & 0xF
        length = int.from_bytes(data[1 : 1 + noof_bytes], byteorder="little")
        value, remaining = (
            data[1 + noof_bytes : 1 + noof_bytes + length].decode("utf-8"),
            data[1 + noof_bytes + length :],
        )
    elif 0x70 <= data[0] <= 0x90:
        length = data[0] - 0x70
        value, remaining = data[1 : 1 + length], data[1 + length :]
    elif 0x90 < data[0] <= 0x94:
        noof_bytes = data[0] & 0xF
        length = int.from_bytes(data[1 : 1 + noof_bytes], byteorder="little")
        value, remaining = (
            data[1 + noof_bytes : 1 + noof_bytes + length],
            data[1 + noof_bytes + length :],
        )
    elif (data[0] & 0xF0) == 0xD0:
        count = data[0] & 0xF
        output = []
        ptr = data[1:]
        if count == 0xF:  # Endless list
            while ptr[0] != 0x03:
                value, ptr = _unpack(ptr, object_list)
                output.append(value)
            ptr = ptr[1:]
        else:
            for _ in range(count):
                value, ptr = _unpack(ptr, object_list)
                output.append(value)
        value, remaining = output, ptr
        add_to_object_list = False
    elif (data[0] & 0xE0) == 0xE0:
        count = data[0] & 0xF
        output = {}
        ptr = data[1:]
        if count == 0xF:  # Endless dict
            while ptr[0] != 0x03:
                key, ptr = _unpack(ptr, object_list)
                value, ptr = _unpack(ptr, object_list)
                output[key] = value
            ptr = ptr[1:]
        else:
            for _ in range(count):
                key, ptr = _unpack(ptr, object_list)
                value, ptr = _unpack(ptr, object_list)
                output[key] = value
        value, remaining = output, ptr
        add_to_object_list = False
    elif 0xA0 <= data[0] <= 0xBF:
        value, remaining = object_list[data[0] - 0xA0], data[1:]
    elif 0xC1 <= data[0] <= 0xC4:
        length = data[0] - 0xC0
        value, remaining = (
            UID(int.from_bytes(data[1 : 1 + length], byteorder="big")),
            data[1 + length :],
        )
    else:
        raise TypeError(hex(data[0]))

    if add_to_object_list and value not in object_list:
        object_list.append(value)

    return value, remaining
