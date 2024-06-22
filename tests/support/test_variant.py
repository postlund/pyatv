"""Unit tests for pyatv.protocols.mrp.variant."""

import pytest

from pyatv.support.variant import read_variant, write_variant


def test_read_single_byte():
    assert read_variant(b"\x00")[0] == 0x00
    assert read_variant(b"\x35")[0] == 0x35


def test_read_multiple_bytes():
    assert read_variant(b"\xb5\x44")[0] == 8757
    assert read_variant(b"\xc5\x92\x01")[0] == 18757


def test_read_and_return_remaining_data():
    value, remaining = read_variant(b"\xb5\x44\xca\xfe")
    assert value == 8757
    assert remaining == b"\xca\xfe"


def test_read_invalid_variant():
    with pytest.raises(Exception):
        read_variant(b"\x80")


def test_write_single_byte():
    assert write_variant(0x00) == b"\x00"
    assert write_variant(0x35) == b"\x35"


def test_write_multiple_bytes():
    assert write_variant(8757) == b"\xb5\x44"
    assert write_variant(18757) == b"\xc5\x92\x01"
