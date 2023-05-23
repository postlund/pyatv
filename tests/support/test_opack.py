"""Unit tests for pyatv.protocols.companion.opack.

TODO: Add integration tests using pack and unpack together.
"""
from datetime import datetime
from uuid import UUID

from deepdiff import DeepDiff
import pytest

from pyatv.support.opack import pack, unpack

# pack


def test_pack_unsupported_type():
    with pytest.raises(TypeError):
        pack(set())


def test_pack_boolean():
    assert pack(True) == b"\x01"
    assert pack(False) == b"\x02"


def test_pack_none():
    assert pack(None) == b"\x04"


def test_pack_uuid():
    assert (
        pack(UUID("{12345678-1234-5678-1234-567812345678}"))
        == b"\x05\x124Vx\x124Vx\x124Vx\x124Vx"
    )


def test_pack_absolute_time():
    with pytest.raises(NotImplementedError):
        pack(datetime.now())


def test_pack_small_integers():
    assert pack(0) == b"\x08"
    assert pack(0xF) == b"\x17"
    assert pack(0x27) == b"\x2F"


def test_pack_larger_integers():
    assert pack(0x28) == b"\x30\x28"
    assert pack(0x1FF) == b"\x31\xFF\x01"
    assert pack(0x1FFFFFF) == b"\x32\xFF\xFF\xFF\x01"
    assert pack(0x1FFFFFFFFFFFFFF) == b"\x33\xFF\xFF\xFF\xFF\xFF\xFF\xFF\x01"


def test_pack_float64():
    assert pack(1.0) == b"\x36\x00\x00\x00\x00\x00\x00\xF0\x3F"


def test_pack_short_strings():
    assert pack("a") == b"\x41\x61"
    assert pack("abc") == b"\x43\x61\x62\x63"
    assert pack(0x20 * "a") == b"\x60" + (0x20 * b"\x61")


def test_pack_longer_strings():
    assert pack(33 * "a") == b"\x61\x21" + (33 * b"\x61")
    assert pack(256 * "a") == b"\x62\x00\x01" + (256 * b"\x61")


def test_pack_short_raw_bytes():
    assert pack(b"\xac") == b"\x71\xac"
    assert pack(b"\x12\x34\x56") == b"\x73\x12\x34\x56"
    assert pack(0x20 * b"\xad") == b"\x90" + (0x20 * b"\xad")


def test_pack_longer_raw_bytes():
    assert pack(33 * b"\x61") == b"\x91\x21" + (33 * b"\x61")
    assert pack(256 * b"\x61") == b"\x92\x00\x01" + (256 * b"\x61")


def test_pack_array():
    assert pack([]) == b"\xd0"
    assert pack([1, "test", False]) == b"\xd3\x09\x44\x74\x65\x73\x74\x02"
    assert pack([[True]]) == b"\xd1\xd1\x01"


def test_pack_endless_array():
    assert pack(15 * ["a"]) == b"\xDF\x41\x61" + 14 * b"\xa0" + b"\x03"


def test_pack_dict():
    assert pack({}) == b"\xe0"
    assert pack({"a": 12, False: None}) == b"\xe2\x41\x61\x14\x02\x04"
    assert pack({True: {"a": 2}}) == b"\xe1\x01\xe1\x41\x61\x0a"


def test_pack_endless_dict():
    assert pack(dict((chr(x), chr(x + 1)) for x in range(97, 127, 2))) == (
        b"\xEF" + b"\x41" + b"\x41".join(bytes([x]) for x in range(97, 127)) + b"\x03"
    )


def test_pack_ptr():
    assert pack(["a", "a"]) == b"\xD2\x41\x61\xA0"
    assert (
        pack(["foo", "bar", "foo", "bar"])
        == b"\xD4\x43\x66\x6F\x6F\x43\x62\x61\x72\xA0\xA1"
    )
    assert (
        pack({"a": "b", "c": {"d": "a"}, "d": True})
        == b"\xE3\x41\x61\x41\x62\x41\x63\xE1\x41\x64\xA0\xA3\x01"
    )


def test_pack_more_ptr():
    data = list(chr(x).encode() for x in range(257))
    assert (
        pack(data + data)
        == b"\xDF\x71\x00\x71\x01\x71\x02\x71\x03\x71\x04\x71\x05\x71\x06\x71"
        b"\x07\x71\x08\x71\x09\x71\x0A\x71\x0B\x71\x0C\x71\x0D\x71\x0E\x71"
        b"\x0F\x71\x10\x71\x11\x71\x12\x71\x13\x71\x14\x71\x15\x71\x16\x71"
        b"\x17\x71\x18\x71\x19\x71\x1A\x71\x1B\x71\x1C\x71\x1D\x71\x1E\x71"
        b"\x1F\x71\x20\x71\x21\x71\x22\x71\x23\x71\x24\x71\x25\x71\x26\x71"
        b"\x27\x71\x28\x71\x29\x71\x2A\x71\x2B\x71\x2C\x71\x2D\x71\x2E\x71"
        b"\x2F\x71\x30\x71\x31\x71\x32\x71\x33\x71\x34\x71\x35\x71\x36\x71"
        b"\x37\x71\x38\x71\x39\x71\x3A\x71\x3B\x71\x3C\x71\x3D\x71\x3E\x71"
        b"\x3F\x71\x40\x71\x41\x71\x42\x71\x43\x71\x44\x71\x45\x71\x46\x71"
        b"\x47\x71\x48\x71\x49\x71\x4A\x71\x4B\x71\x4C\x71\x4D\x71\x4E\x71"
        b"\x4F\x71\x50\x71\x51\x71\x52\x71\x53\x71\x54\x71\x55\x71\x56\x71"
        b"\x57\x71\x58\x71\x59\x71\x5A\x71\x5B\x71\x5C\x71\x5D\x71\x5E\x71"
        b"\x5F\x71\x60\x71\x61\x71\x62\x71\x63\x71\x64\x71\x65\x71\x66\x71"
        b"\x67\x71\x68\x71\x69\x71\x6A\x71\x6B\x71\x6C\x71\x6D\x71\x6E\x71"
        b"\x6F\x71\x70\x71\x71\x71\x72\x71\x73\x71\x74\x71\x75\x71\x76\x71"
        b"\x77\x71\x78\x71\x79\x71\x7A\x71\x7B\x71\x7C\x71\x7D\x71\x7E\x71"
        b"\x7F\x72\xC2\x80\x72\xC2\x81\x72\xC2\x82\x72\xC2\x83\x72\xC2\x84"
        b"\x72\xC2\x85\x72\xC2\x86\x72\xC2\x87\x72\xC2\x88\x72\xC2\x89\x72"
        b"\xC2\x8A\x72\xC2\x8B\x72\xC2\x8C\x72\xC2\x8D\x72\xC2\x8E\x72\xC2"
        b"\x8F\x72\xC2\x90\x72\xC2\x91\x72\xC2\x92\x72\xC2\x93\x72\xC2\x94"
        b"\x72\xC2\x95\x72\xC2\x96\x72\xC2\x97\x72\xC2\x98\x72\xC2\x99\x72"
        b"\xC2\x9A\x72\xC2\x9B\x72\xC2\x9C\x72\xC2\x9D\x72\xC2\x9E\x72\xC2"
        b"\x9F\x72\xC2\xA0\x72\xC2\xA1\x72\xC2\xA2\x72\xC2\xA3\x72\xC2\xA4"
        b"\x72\xC2\xA5\x72\xC2\xA6\x72\xC2\xA7\x72\xC2\xA8\x72\xC2\xA9\x72"
        b"\xC2\xAA\x72\xC2\xAB\x72\xC2\xAC\x72\xC2\xAD\x72\xC2\xAE\x72\xC2"
        b"\xAF\x72\xC2\xB0\x72\xC2\xB1\x72\xC2\xB2\x72\xC2\xB3\x72\xC2\xB4"
        b"\x72\xC2\xB5\x72\xC2\xB6\x72\xC2\xB7\x72\xC2\xB8\x72\xC2\xB9\x72"
        b"\xC2\xBA\x72\xC2\xBB\x72\xC2\xBC\x72\xC2\xBD\x72\xC2\xBE\x72\xC2"
        b"\xBF\x72\xC3\x80\x72\xC3\x81\x72\xC3\x82\x72\xC3\x83\x72\xC3\x84"
        b"\x72\xC3\x85\x72\xC3\x86\x72\xC3\x87\x72\xC3\x88\x72\xC3\x89\x72"
        b"\xC3\x8A\x72\xC3\x8B\x72\xC3\x8C\x72\xC3\x8D\x72\xC3\x8E\x72\xC3"
        b"\x8F\x72\xC3\x90\x72\xC3\x91\x72\xC3\x92\x72\xC3\x93\x72\xC3\x94"
        b"\x72\xC3\x95\x72\xC3\x96\x72\xC3\x97\x72\xC3\x98\x72\xC3\x99\x72"
        b"\xC3\x9A\x72\xC3\x9B\x72\xC3\x9C\x72\xC3\x9D\x72\xC3\x9E\x72\xC3"
        b"\x9F\x72\xC3\xA0\x72\xC3\xA1\x72\xC3\xA2\x72\xC3\xA3\x72\xC3\xA4"
        b"\x72\xC3\xA5\x72\xC3\xA6\x72\xC3\xA7\x72\xC3\xA8\x72\xC3\xA9\x72"
        b"\xC3\xAA\x72\xC3\xAB\x72\xC3\xAC\x72\xC3\xAD\x72\xC3\xAE\x72\xC3"
        b"\xAF\x72\xC3\xB0\x72\xC3\xB1\x72\xC3\xB2\x72\xC3\xB3\x72\xC3\xB4"
        b"\x72\xC3\xB5\x72\xC3\xB6\x72\xC3\xB7\x72\xC3\xB8\x72\xC3\xB9\x72"
        b"\xC3\xBA\x72\xC3\xBB\x72\xC3\xBC\x72\xC3\xBD\x72\xC3\xBE\x72\xC3"
        b"\xBF\x72\xC4\x80\xA0\xA1\xA2\xA3\xA4\xA5\xA6\xA7\xA8\xA9\xAA\xAB"
        b"\xAC\xAD\xAE\xAF\xB0\xB1\xB2\xB3\xB4\xB5\xB6\xB7\xB8\xB9\xBA\xBB"
        b"\xBC\xBD\xBE\xBF\xC0\xC1\x21\xC1\x22\xC1\x23\xC1\x24\xC1\x25\xC1"
        b"\x26\xC1\x27\xC1\x28\xC1\x29\xC1\x2A\xC1\x2B\xC1\x2C\xC1\x2D\xC1"
        b"\x2E\xC1\x2F\xC1\x30\xC1\x31\xC1\x32\xC1\x33\xC1\x34\xC1\x35\xC1"
        b"\x36\xC1\x37\xC1\x38\xC1\x39\xC1\x3A\xC1\x3B\xC1\x3C\xC1\x3D\xC1"
        b"\x3E\xC1\x3F\xC1\x40\xC1\x41\xC1\x42\xC1\x43\xC1\x44\xC1\x45\xC1"
        b"\x46\xC1\x47\xC1\x48\xC1\x49\xC1\x4A\xC1\x4B\xC1\x4C\xC1\x4D\xC1"
        b"\x4E\xC1\x4F\xC1\x50\xC1\x51\xC1\x52\xC1\x53\xC1\x54\xC1\x55\xC1"
        b"\x56\xC1\x57\xC1\x58\xC1\x59\xC1\x5A\xC1\x5B\xC1\x5C\xC1\x5D\xC1"
        b"\x5E\xC1\x5F\xC1\x60\xC1\x61\xC1\x62\xC1\x63\xC1\x64\xC1\x65\xC1"
        b"\x66\xC1\x67\xC1\x68\xC1\x69\xC1\x6A\xC1\x6B\xC1\x6C\xC1\x6D\xC1"
        b"\x6E\xC1\x6F\xC1\x70\xC1\x71\xC1\x72\xC1\x73\xC1\x74\xC1\x75\xC1"
        b"\x76\xC1\x77\xC1\x78\xC1\x79\xC1\x7A\xC1\x7B\xC1\x7C\xC1\x7D\xC1"
        b"\x7E\xC1\x7F\xC1\x80\xC1\x81\xC1\x82\xC1\x83\xC1\x84\xC1\x85\xC1"
        b"\x86\xC1\x87\xC1\x88\xC1\x89\xC1\x8A\xC1\x8B\xC1\x8C\xC1\x8D\xC1"
        b"\x8E\xC1\x8F\xC1\x90\xC1\x91\xC1\x92\xC1\x93\xC1\x94\xC1\x95\xC1"
        b"\x96\xC1\x97\xC1\x98\xC1\x99\xC1\x9A\xC1\x9B\xC1\x9C\xC1\x9D\xC1"
        b"\x9E\xC1\x9F\xC1\xA0\xC1\xA1\xC1\xA2\xC1\xA3\xC1\xA4\xC1\xA5\xC1"
        b"\xA6\xC1\xA7\xC1\xA8\xC1\xA9\xC1\xAA\xC1\xAB\xC1\xAC\xC1\xAD\xC1"
        b"\xAE\xC1\xAF\xC1\xB0\xC1\xB1\xC1\xB2\xC1\xB3\xC1\xB4\xC1\xB5\xC1"
        b"\xB6\xC1\xB7\xC1\xB8\xC1\xB9\xC1\xBA\xC1\xBB\xC1\xBC\xC1\xBD\xC1"
        b"\xBE\xC1\xBF\xC1\xC0\xC1\xC1\xC1\xC2\xC1\xC3\xC1\xC4\xC1\xC5\xC1"
        b"\xC6\xC1\xC7\xC1\xC8\xC1\xC9\xC1\xCA\xC1\xCB\xC1\xCC\xC1\xCD\xC1"
        b"\xCE\xC1\xCF\xC1\xD0\xC1\xD1\xC1\xD2\xC1\xD3\xC1\xD4\xC1\xD5\xC1"
        b"\xD6\xC1\xD7\xC1\xD8\xC1\xD9\xC1\xDA\xC1\xDB\xC1\xDC\xC1\xDD\xC1"
        b"\xDE\xC1\xDF\xC1\xE0\xC1\xE1\xC1\xE2\xC1\xE3\xC1\xE4\xC1\xE5\xC1"
        b"\xE6\xC1\xE7\xC1\xE8\xC1\xE9\xC1\xEA\xC1\xEB\xC1\xEC\xC1\xED\xC1"
        b"\xEE\xC1\xEF\xC1\xF0\xC1\xF1\xC1\xF2\xC1\xF3\xC1\xF4\xC1\xF5\xC1"
        b"\xF6\xC1\xF7\xC1\xF8\xC1\xF9\xC1\xFA\xC1\xFB\xC1\xFC\xC1\xFD\xC1"
        b"\xFE\xC1\xFF\xC2\x00\x01\x03"
    )


# unpack


def test_unpack_unsupported_type():
    with pytest.raises(TypeError):
        unpack(b"\x00")


def test_unpack_boolean():
    assert unpack(b"\x01") == (True, b"")
    assert unpack(b"\x02") == (False, b"")


def test_unpack_none():
    assert unpack(b"\x04") == (None, b"")


def test_unpack_uuid():
    assert unpack(b"\x05\x124Vx\x124Vx\x124Vx\x124Vx") == (
        UUID("{12345678-1234-5678-1234-567812345678}"),
        b"",
    )


def test_unpack_absolute_time():
    # TODO: This is not implemented, it only parses the time stamp as an integer
    assert unpack(b"\x06\x01\x00\x00\x00\x00\x00\x00\x00") == (1, b"")


def test_unpack_small_integers():
    assert unpack(b"\x08") == (0, b"")
    assert unpack(b"\x17") == (0xF, b"")
    assert unpack(b"\x2F") == (0x27, b"")


def test_unpack_larger_integers():
    assert unpack(b"\x30\x28") == (0x28, b"")
    assert unpack(b"\x31\xFf\x01") == (0x1FF, b"")
    assert unpack(b"\x32\xFF\xFF\x01") == (0x1FFFF, b"")
    assert unpack(b"\x33\xFF\xFF\xFF\x01") == (0x1FFFFFF, b"")


def test_pack_unfloat32():
    assert unpack(b"\x35\x00\x00\x80\x3f") == (1.0, b"")


def test_unpack_float64():
    assert unpack(b"\x36\x00\x00\x00\x00\x00\x00\xF0\x3F") == (1.0, b"")


def test_unpack_short_strings():
    assert unpack(b"\x41\x61") == ("a", b"")
    assert unpack(b"\x43\x61\x62\x63") == ("abc", b"")
    assert unpack(b"\x60" + (0x20 * b"\x61")) == (0x20 * "a", b"")


def test_unpack_longer_strings():
    assert unpack(b"\x61\x21" + (33 * b"\x61")) == (33 * "a", b"")
    assert unpack(b"\x62\x00\x01" + (256 * b"\x61")) == (256 * "a", b"")


def test_unpack_short_raw_bytes():
    assert unpack(b"\x71\xac") == (b"\xac", b"")
    assert unpack(b"\x73\x12\x34\x56") == (b"\x12\x34\x56", b"")
    assert unpack(b"\x90" + (0x20 * b"\xad")) == (0x20 * b"\xad", b"")


def test_unpack_longer_raw_bytes():
    assert unpack(b"\x91\x21" + (33 * b"\x61")) == (33 * b"\x61", b"")
    assert unpack(b"\x92\x00\x01" + (256 * b"\x61")) == (256 * b"\x61", b"")


def test_unpack_array():
    assert unpack(b"\xd0") == ([], b"")
    assert unpack(b"\xd3\x09\x44\x74\x65\x73\x74\x02") == ([1, "test", False], b"")
    assert unpack(b"\xd1\xd1\x01") == ([[True]], b"")


def test_unpack_endless_array():
    list1 = b"\xDF\x41\x61" + 15 * b"\xa0" + b"\x03"
    list2 = b"\xDF\x41\x62" + 15 * b"\xa1" + b"\x03"
    assert unpack(list1) == (16 * ["a"], b"")
    assert unpack(b"\xD2" + list1 + list2) == ([16 * ["a"], 16 * ["b"]], b"")


def test_unpack_dict():
    assert unpack(b"\xe0") == ({}, b"")
    assert unpack(b"\xe2\x41\x61\x14\x02\x04") == ({"a": 12, False: None}, b"")
    assert unpack(b"\xe1\x01\xe1\x41\x61\x0a") == ({True: {"a": 2}}, b"")


def test_unpack_endless_dict():
    assert unpack(
        b"\xEF" + b"\x41" + b"\x41".join(bytes([x]) for x in range(97, 127)) + b"\x03"
    ) == (dict((chr(x), chr(x + 1)) for x in range(97, 127, 2)), b"")


def test_unpack_ptr():
    assert unpack(b"\xD2\x41\x61\xA0") == (["a", "a"], b"")
    assert unpack(b"\xD4\x43\x66\x6F\x6F\x43\x62\x61\x72\xA0\xA1") == (
        ["foo", "bar", "foo", "bar"],
        b"",
    )
    assert unpack(b"\xE3\x41\x61\x41\x62\x41\x63\xE1\x41\x64\xA0\xA3\x01") == (
        {"a": "b", "c": {"d": "a"}, "d": True},
        b"",
    )


def test_unpack_more_ptr():
    data = list(chr(x).encode() for x in range(257))
    assert unpack(
        b"\xDF\x71\x00\x71\x01\x71\x02\x71\x03\x71\x04\x71\x05\x71\x06\x71"
        b"\x07\x71\x08\x71\x09\x71\x0A\x71\x0B\x71\x0C\x71\x0D\x71\x0E\x71"
        b"\x0F\x71\x10\x71\x11\x71\x12\x71\x13\x71\x14\x71\x15\x71\x16\x71"
        b"\x17\x71\x18\x71\x19\x71\x1A\x71\x1B\x71\x1C\x71\x1D\x71\x1E\x71"
        b"\x1F\x71\x20\x71\x21\x71\x22\x71\x23\x71\x24\x71\x25\x71\x26\x71"
        b"\x27\x71\x28\x71\x29\x71\x2A\x71\x2B\x71\x2C\x71\x2D\x71\x2E\x71"
        b"\x2F\x71\x30\x71\x31\x71\x32\x71\x33\x71\x34\x71\x35\x71\x36\x71"
        b"\x37\x71\x38\x71\x39\x71\x3A\x71\x3B\x71\x3C\x71\x3D\x71\x3E\x71"
        b"\x3F\x71\x40\x71\x41\x71\x42\x71\x43\x71\x44\x71\x45\x71\x46\x71"
        b"\x47\x71\x48\x71\x49\x71\x4A\x71\x4B\x71\x4C\x71\x4D\x71\x4E\x71"
        b"\x4F\x71\x50\x71\x51\x71\x52\x71\x53\x71\x54\x71\x55\x71\x56\x71"
        b"\x57\x71\x58\x71\x59\x71\x5A\x71\x5B\x71\x5C\x71\x5D\x71\x5E\x71"
        b"\x5F\x71\x60\x71\x61\x71\x62\x71\x63\x71\x64\x71\x65\x71\x66\x71"
        b"\x67\x71\x68\x71\x69\x71\x6A\x71\x6B\x71\x6C\x71\x6D\x71\x6E\x71"
        b"\x6F\x71\x70\x71\x71\x71\x72\x71\x73\x71\x74\x71\x75\x71\x76\x71"
        b"\x77\x71\x78\x71\x79\x71\x7A\x71\x7B\x71\x7C\x71\x7D\x71\x7E\x71"
        b"\x7F\x72\xC2\x80\x72\xC2\x81\x72\xC2\x82\x72\xC2\x83\x72\xC2\x84"
        b"\x72\xC2\x85\x72\xC2\x86\x72\xC2\x87\x72\xC2\x88\x72\xC2\x89\x72"
        b"\xC2\x8A\x72\xC2\x8B\x72\xC2\x8C\x72\xC2\x8D\x72\xC2\x8E\x72\xC2"
        b"\x8F\x72\xC2\x90\x72\xC2\x91\x72\xC2\x92\x72\xC2\x93\x72\xC2\x94"
        b"\x72\xC2\x95\x72\xC2\x96\x72\xC2\x97\x72\xC2\x98\x72\xC2\x99\x72"
        b"\xC2\x9A\x72\xC2\x9B\x72\xC2\x9C\x72\xC2\x9D\x72\xC2\x9E\x72\xC2"
        b"\x9F\x72\xC2\xA0\x72\xC2\xA1\x72\xC2\xA2\x72\xC2\xA3\x72\xC2\xA4"
        b"\x72\xC2\xA5\x72\xC2\xA6\x72\xC2\xA7\x72\xC2\xA8\x72\xC2\xA9\x72"
        b"\xC2\xAA\x72\xC2\xAB\x72\xC2\xAC\x72\xC2\xAD\x72\xC2\xAE\x72\xC2"
        b"\xAF\x72\xC2\xB0\x72\xC2\xB1\x72\xC2\xB2\x72\xC2\xB3\x72\xC2\xB4"
        b"\x72\xC2\xB5\x72\xC2\xB6\x72\xC2\xB7\x72\xC2\xB8\x72\xC2\xB9\x72"
        b"\xC2\xBA\x72\xC2\xBB\x72\xC2\xBC\x72\xC2\xBD\x72\xC2\xBE\x72\xC2"
        b"\xBF\x72\xC3\x80\x72\xC3\x81\x72\xC3\x82\x72\xC3\x83\x72\xC3\x84"
        b"\x72\xC3\x85\x72\xC3\x86\x72\xC3\x87\x72\xC3\x88\x72\xC3\x89\x72"
        b"\xC3\x8A\x72\xC3\x8B\x72\xC3\x8C\x72\xC3\x8D\x72\xC3\x8E\x72\xC3"
        b"\x8F\x72\xC3\x90\x72\xC3\x91\x72\xC3\x92\x72\xC3\x93\x72\xC3\x94"
        b"\x72\xC3\x95\x72\xC3\x96\x72\xC3\x97\x72\xC3\x98\x72\xC3\x99\x72"
        b"\xC3\x9A\x72\xC3\x9B\x72\xC3\x9C\x72\xC3\x9D\x72\xC3\x9E\x72\xC3"
        b"\x9F\x72\xC3\xA0\x72\xC3\xA1\x72\xC3\xA2\x72\xC3\xA3\x72\xC3\xA4"
        b"\x72\xC3\xA5\x72\xC3\xA6\x72\xC3\xA7\x72\xC3\xA8\x72\xC3\xA9\x72"
        b"\xC3\xAA\x72\xC3\xAB\x72\xC3\xAC\x72\xC3\xAD\x72\xC3\xAE\x72\xC3"
        b"\xAF\x72\xC3\xB0\x72\xC3\xB1\x72\xC3\xB2\x72\xC3\xB3\x72\xC3\xB4"
        b"\x72\xC3\xB5\x72\xC3\xB6\x72\xC3\xB7\x72\xC3\xB8\x72\xC3\xB9\x72"
        b"\xC3\xBA\x72\xC3\xBB\x72\xC3\xBC\x72\xC3\xBD\x72\xC3\xBE\x72\xC3"
        b"\xBF\x72\xC4\x80\xA0\xA1\xA2\xA3\xA4\xA5\xA6\xA7\xA8\xA9\xAA\xAB"
        b"\xAC\xAD\xAE\xAF\xB0\xB1\xB2\xB3\xB4\xB5\xB6\xB7\xB8\xB9\xBA\xBB"
        b"\xBC\xBD\xBE\xBF\xC0\xC1\x21\xC1\x22\xC1\x23\xC1\x24\xC1\x25\xC1"
        b"\x26\xC1\x27\xC1\x28\xC1\x29\xC1\x2A\xC1\x2B\xC1\x2C\xC1\x2D\xC1"
        b"\x2E\xC1\x2F\xC1\x30\xC1\x31\xC1\x32\xC1\x33\xC1\x34\xC1\x35\xC1"
        b"\x36\xC1\x37\xC1\x38\xC1\x39\xC1\x3A\xC1\x3B\xC1\x3C\xC1\x3D\xC1"
        b"\x3E\xC1\x3F\xC1\x40\xC1\x41\xC1\x42\xC1\x43\xC1\x44\xC1\x45\xC1"
        b"\x46\xC1\x47\xC1\x48\xC1\x49\xC1\x4A\xC1\x4B\xC1\x4C\xC1\x4D\xC1"
        b"\x4E\xC1\x4F\xC1\x50\xC1\x51\xC1\x52\xC1\x53\xC1\x54\xC1\x55\xC1"
        b"\x56\xC1\x57\xC1\x58\xC1\x59\xC1\x5A\xC1\x5B\xC1\x5C\xC1\x5D\xC1"
        b"\x5E\xC1\x5F\xC1\x60\xC1\x61\xC1\x62\xC1\x63\xC1\x64\xC1\x65\xC1"
        b"\x66\xC1\x67\xC1\x68\xC1\x69\xC1\x6A\xC1\x6B\xC1\x6C\xC1\x6D\xC1"
        b"\x6E\xC1\x6F\xC1\x70\xC1\x71\xC1\x72\xC1\x73\xC1\x74\xC1\x75\xC1"
        b"\x76\xC1\x77\xC1\x78\xC1\x79\xC1\x7A\xC1\x7B\xC1\x7C\xC1\x7D\xC1"
        b"\x7E\xC1\x7F\xC1\x80\xC1\x81\xC1\x82\xC1\x83\xC1\x84\xC1\x85\xC1"
        b"\x86\xC1\x87\xC1\x88\xC1\x89\xC1\x8A\xC1\x8B\xC1\x8C\xC1\x8D\xC1"
        b"\x8E\xC1\x8F\xC1\x90\xC1\x91\xC1\x92\xC1\x93\xC1\x94\xC1\x95\xC1"
        b"\x96\xC1\x97\xC1\x98\xC1\x99\xC1\x9A\xC1\x9B\xC1\x9C\xC1\x9D\xC1"
        b"\x9E\xC1\x9F\xC1\xA0\xC1\xA1\xC1\xA2\xC1\xA3\xC1\xA4\xC1\xA5\xC1"
        b"\xA6\xC1\xA7\xC1\xA8\xC1\xA9\xC1\xAA\xC1\xAB\xC1\xAC\xC1\xAD\xC1"
        b"\xAE\xC1\xAF\xC1\xB0\xC1\xB1\xC1\xB2\xC1\xB3\xC1\xB4\xC1\xB5\xC1"
        b"\xB6\xC1\xB7\xC1\xB8\xC1\xB9\xC1\xBA\xC1\xBB\xC1\xBC\xC1\xBD\xC1"
        b"\xBE\xC1\xBF\xC1\xC0\xC1\xC1\xC1\xC2\xC1\xC3\xC1\xC4\xC1\xC5\xC1"
        b"\xC6\xC1\xC7\xC1\xC8\xC1\xC9\xC1\xCA\xC1\xCB\xC1\xCC\xC1\xCD\xC1"
        b"\xCE\xC1\xCF\xC1\xD0\xC1\xD1\xC1\xD2\xC1\xD3\xC1\xD4\xC1\xD5\xC1"
        b"\xD6\xC1\xD7\xC1\xD8\xC1\xD9\xC1\xDA\xC1\xDB\xC1\xDC\xC1\xDD\xC1"
        b"\xDE\xC1\xDF\xC1\xE0\xC1\xE1\xC1\xE2\xC1\xE3\xC1\xE4\xC1\xE5\xC1"
        b"\xE6\xC1\xE7\xC1\xE8\xC1\xE9\xC1\xEA\xC1\xEB\xC1\xEC\xC1\xED\xC1"
        b"\xEE\xC1\xEF\xC1\xF0\xC1\xF1\xC1\xF2\xC1\xF3\xC1\xF4\xC1\xF5\xC1"
        b"\xF6\xC1\xF7\xC1\xF8\xC1\xF9\xC1\xFA\xC1\xFB\xC1\xFC\xC1\xFD\xC1"
        b"\xFE\xC1\xFF\xC2\x00\x01\x03"
    ) == (data + data, b"")


def test_unpack_uid():
    assert unpack(b"\xDF\x30\x01\x30\x02\xC1\x01\x03") == ([1, 2, 2], b"")
    assert unpack(b"\xDF\x30\x01\x30\x02\xC2\x01\x00\x03") == ([1, 2, 2], b"")
    assert unpack(b"\xDF\x30\x01\x30\x02\xC3\x01\x00\x00\x03") == ([1, 2, 2], b"")
    assert unpack(b"\xDF\x30\x01\x30\x02\xC4\x01\x00\x00\x00\x03") == ([1, 2, 2], b"")


def test_golden():
    data = {
        "_i": "_systemInfo",
        "_x": 1254122577,
        "_btHP": False,
        "_c": {
            "_pubID": "AA:BB:CC:DD:EE:FF",
            "_sv": "230.1",
            "_bf": 0,
            "_siriInfo": {
                "collectorElectionVersion": 1.0,
                "deviceCapabilities": {"seymourEnabled": 1, "voiceTriggerEnabled": 2},
                "sharedDataProtoBuf": 512 * b"\x08",
            },
            "_stA": [
                "com.apple.LiveAudio",
                "com.apple.siri.wakeup",
                "com.apple.Seymour",
                "com.apple.announce",
                "com.apple.coreduet.sync",
                "com.apple.SeymourSession",
            ],
            "_i": "6c62fca18b11",
            "_clFl": 128,
            "_idsID": "44E14ABC-DDDD-4188-B661-11BAAAF6ECDE",
            "_hkUID": [UUID("17ed160a-81f8-4488-962c-6b1a83eb0081")],
            "_dC": "1",
            "_sf": 256,
            "model": "iPhone10,6",
            "name": "iPhone",
        },
        "_t": 2,
    }

    packed = pack(data)
    unpacked = unpack(packed)

    assert DeepDiff(unpacked, data, ignore_order=True)
