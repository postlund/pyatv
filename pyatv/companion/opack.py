"""Support for the OPACK serialization format.

NB: This implementation is not complete (some things missing and some things not
implemented yet). It also has a lot of code duplication. Clean ups are needed.

NB2: This id also best-effort so far and only verified with a few real test cases.
"""
import struct
from datetime import datetime


def pack(data):
    """Pack data structure with OPACK and return bytes."""
    if data is None:
        return b"\x04"
    if isinstance(data, bool):
        return bytes([1 if data else 2])
    if isinstance(data, datetime):
        raise NotImplementedError("absolute time")
    if isinstance(data, int):
        if data < 0x28:
            return bytes([data + 8])
        if data <= 0xFF:
            return bytes([0x30]) + data.to_bytes(1, byteorder="big")
        if data <= 0xFFFF:
            return bytes([0x31]) + data.to_bytes(2, byteorder="big")
        if data <= 0xFFFFFF:
            return bytes([0x32]) + data.to_bytes(3, byteorder="big")
        if data <= 0xFFFFFFFF:
            return bytes([0x33]) + data.to_bytes(4, byteorder="big")
    if isinstance(data, float):
        return struct.pack(">d", data)
    if isinstance(data, str):
        encoded = data.encode("utf-8")
        if len(encoded) <= 0x20:
            return bytes([0x40 + len(encoded)]) + encoded
        if len(encoded) <= 0xFF:
            return bytes([0x61]) + len(encoded).to_bytes(1, byteorder="big") + encoded
        if len(encoded) <= 0xFFFF:
            return bytes([0x62]) + len(encoded).to_bytes(2, byteorder="big") + encoded
        if len(encoded) <= 0xFFFFFF:
            return bytes([0x63]) + len(encoded).to_bytes(3, byteorder="big") + encoded
        if len(encoded) <= 0xFFFFFFFF:
            return bytes([0x64]) + len(encoded).to_bytes(4, byteorder="big") + encoded
    if isinstance(data, bytes):
        if len(data) <= 0x20:
            return bytes([0x70 + len(data)]) + data
        if len(data) <= 0xFF:
            return bytes([0x91]) + len(data).to_bytes(1, byteorder="big") + data
        if len(data) <= 0xFFFF:
            return bytes([0x92]) + len(data).to_bytes(2, byteorder="big") + data
        if len(data) <= 0xFFFFFF:
            return bytes([0x93]) + len(data).to_bytes(3, byteorder="big") + data
        if len(data) <= 0xFFFFFFFF:
            return bytes([0x94]) + len(data).to_bytes(4, byteorder="big") + data
    if isinstance(data, list):
        return bytes([0xD0 + len(data)]) + b"".join(pack(x) for x in data)
    if isinstance(data, dict):
        return bytes([0xE0 + len(data)]) + b"".join(
            pack(k) + pack(v) for k, v in data.items()
        )

    raise TypeError(str(type(data)))


def unpack(data):
    """Unpack raw OPACK data into python objects."""
    if data[0] == 0x01:
        return True, data[1:]
    if data[0] == 0x02:
        return False, data[1:]
    if data == b"\x04":
        return None, data[1:]
    if data == b"\x06":
        raise NotImplementedError("absolute time")
    if 0x08 <= data[0] <= 0x2F:
        return data[0] - 8, data[1:]
    if data[0] == 0x35:
        return struct.unpack(">f", data[1:5])[0], data[5:]
    if data[0] == 0x36:
        return struct.unpack(">d", data[1:9])[0], data[9:]
    if (data[0] & 0xF0) == 0x30:
        noof_bytes = (data[0] & 0xF) + 1
        return (
            int.from_bytes(data[1 : 1 + noof_bytes], byteorder="big"),
            data[1 + noof_bytes :],
        )
    if 0x40 <= data[0] <= 0x60:
        length = data[0] - 0x40
        return data[1 : 1 + length].decode("utf-8"), data[1 + length :]
    if 0x60 < data[0] <= 0x64:
        noof_bytes = data[0] & 0xF
        length = int.from_bytes(data[1 : 1 + noof_bytes], byteorder="big")
        return (
            data[1 + noof_bytes : 1 + noof_bytes + length].decode("utf-8"),
            data[1 + noof_bytes + length :],
        )
    if 0x70 <= data[0] <= 0x90:
        length = data[0] - 0x70
        return data[1 : 1 + length], data[1 + length :]
    if 0x90 < data[0] <= 0x94:
        noof_bytes = data[0] & 0xF
        length = int.from_bytes(data[1 : 1 + noof_bytes], byteorder="big")
        return (
            data[1 + noof_bytes : 1 + noof_bytes + length],
            data[1 + noof_bytes + length :],
        )
    if (data[0] & 0xF0) == 0xD0:
        count = data[0] & 0xF
        output = []
        ptr = data[1:]
        for _ in range(count):
            value, ptr = unpack(ptr)
            output.append(value)
        return output, ptr
    if (data[0] & 0xE0) == 0xE0:
        count = data[0] & 0xF
        output = {}
        ptr = data[1:]
        for _ in range(count):
            key, ptr = unpack(ptr)
            value, ptr = unpack(ptr)
            output[key] = value
        return output, ptr

    raise TypeError(str(type(data)))
