"""Unit tests for pyatv.protocols.companion.opack.

TODO: Add integration tests using pack and unpack together.
"""
from datetime import datetime
from uuid import UUID

from deepdiff import DeepDiff
import pytest

from pyatv.protocols.companion.opack import UID, pack, unpack

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


def test_pack_uid():
    assert pack(UID(0x01)) == b"\xC1\x01"
    assert pack(UID(0x0102)) == b"\xC2\x01\x02"
    assert pack(UID(0x010203)) == b"\xC3\x01\x02\x03"
    assert pack(UID(0x01020304)) == b"\xC4\x01\x02\x03\x04"


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


def test_unpack_uid():
    assert unpack(b"\xC1\x01") == (UID(0x01), b"")
    assert unpack(b"\xC2\x01\x02") == (UID(0x0102), b"")
    assert unpack(b"\xC3\x01\x02\x03") == (UID(0x010203), b"")
    assert unpack(b"\xC4\x01\x02\x03\x04") == (UID(0x01020304), b"")


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
            "uid": UID(0x11223344),
        },
        "_t": 2,
    }

    packed = pack(data)
    unpacked = unpack(packed)

    assert DeepDiff(unpacked, data, ignore_order=True)
