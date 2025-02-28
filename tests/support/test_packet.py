"""Unit tests for pyatv.support.packet."""

import pytest

from pyatv.support.packet import defpacket

Foo = defpacket("Foo", a="c", b="h")
Bar = Foo.extend("Bar", c="I")


def test_encode_messages():
    assert Foo.encode(b"\x16", 0x123) == b"\x16\x01\x23"


def test_decode_message():
    decoded = Foo.decode(b"\x16\x01\x23")
    assert decoded.a == b"\x16"
    assert decoded.b == 0x123


def test_decode_with_excessive_data():
    decoded = Foo.decode(b"\x17\x02\x34\x11\x22\x33", allow_excessive=True)
    assert decoded.a == b"\x17"
    assert decoded.b == 0x234


def test_extend_encode():
    assert Bar.encode(b"\x77", 0x67, 0xAABBCCDD) == b"\x77\x00\x67\xaa\xbb\xcc\xdd"


def test_extend_decode():
    decoded = Bar.decode(b"\x77\x00\x67\xaa\xbb\xcc\xdd")
    assert decoded.a == b"\x77"
    assert decoded.b == 0x0067
    assert decoded.c == 0xAABBCCDD


def test_message_length():
    assert Foo.length == 3
    assert Bar.length == 3 + 4
