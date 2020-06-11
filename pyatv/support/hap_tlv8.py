"""Implementation of TLV8 used by MRP/HomeKit pairing process.

Note that this implementation only supports one level of value, i.e. no dicts
in dicts.
"""

from enum import IntEnum


class TlvValue(IntEnum):
    """Correspond to TLV values in HAP specification."""

    Method = 0x00
    Identifier = 0x01
    Salt = 0x02
    PublicKey = 0x03
    Proof = 0x04
    EncryptedData = 0x05
    SeqNo = 0x06
    Error = 0x07
    BackOff = 0x08
    Certificate = 0x09
    Signature = 0x0A
    Permissions = 0x0B
    FragmentData = 0x0C
    FragmentLast = 0x0D


class ErrorCode(IntEnum):
    """Correspond to error codes in HAP specification."""

    Authentication = 0x02


def read_tlv(data: bytes):
    """Parse TLV8 bytes into a dict.

    If value is larger than 255 bytes, it is split up in multiple chunks. So
    the same tag might occur several times.
    """

    def _parse(data, pos, size, result=None):
        if result is None:
            result = {}
        if pos >= size:
            return result

        tag = int(data[pos])
        length = data[pos + 1]
        value = data[pos + 2 : pos + 2 + length]

        if tag in result:
            result[tag] += value  # value > 255 is split up
        else:
            result[tag] = value
        return _parse(data, pos + 2 + length, size, result)

    return _parse(data, 0, len(data))


def write_tlv(data: dict):
    """Convert a dict to TLV8 bytes.

    NB: This simple implementation assumes all values are bytes!
    """
    tlv = b""
    for key, value in data.items():
        tag = bytes([int(key)])
        length = len(value)
        pos = 0

        # A tag with length > 255 is added multiple times and concatenated into
        # one buffer when reading the TLV again.
        while pos < len(value):
            size = min(length, 255)
            tlv += tag
            tlv += bytes([size])
            tlv += value[pos : pos + size]
            pos += size
            length -= size
    return tlv
