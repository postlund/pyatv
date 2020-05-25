"""Unit tests for pyatv.companion.opack.

TODO: Add integration tests using pack and unpack together.
"""
import pytest
from datetime import datetime

from pyatv.companion.opack import pack, unpack


def test_pack_unsupported_type():
    with pytest.raises(TypeError):
        pack(set())


def test_pack_boolean():
    assert pack(True) == b"\x01"
    assert pack(False) == b"\x02"


def test_pack_none():
    assert pack(None) == b"\x04"


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
    assert pack(0x1FFFF) == b"\x32\xFF\xFF\x01"
    assert pack(0x1FFFFFF) == b"\x33\xFF\xFF\xFF\x01"


def test_pack_float64():
    assert pack(1.23) == b"\x3f\xf3\xae\x14\x7a\xe1\x47\xae"


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


def test_pack_dict():
    assert pack({}) == b"\xe0"
    assert pack({"a": 12, False: None}) == b"\xe2\x41\x61\x14\x02\x04"
    assert pack({True: {"a": 2}}) == b"\xe1\x01\xe1\x41\x61\x0a"


def test_unpack_unsupported_type():
    with pytest.raises(TypeError):
        unpack(b"\x00")


def test_unpack_boolean():
    assert unpack(b"\x01") == (True, b"")
    assert unpack(b"\x02") == (False, b"")


def test_unpack_none():
    assert unpack(b"\x04") == (None, b"")


def test_unpack_absolute_time():
    with pytest.raises(NotImplementedError):
        unpack(b"\x06")  # TODO: Should be 8 byte payload for timestamp?


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
    assert unpack(b"\x35\x3f\xa0\x00\x00") == (1.25, b"")


def test_unpack_float64():
    assert unpack(b"\x36\x3f\xf3\xae\x14\x7a\xe1\x47\xae") == (1.23, b"")


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


def test_unpack_dict():
    assert unpack(b"\xe0") == ({}, b"")
    assert unpack(b"\xe2\x41\x61\x14\x02\x04") == ({"a": 12, False: None}, b"")
    assert unpack(b"\xe1\x01\xe1\x41\x61\x0a") == ({True: {"a": 2}}, b"")
