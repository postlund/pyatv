"""Unit tests for pyatv.support.hap_tlv8."""

from collections import OrderedDict
from pyatv.support.hap_tlv8 import read_tlv, write_tlv

SINGLE_KEY_IN = {"10": b"123"}
SINGLE_KEY_OUT = b"\x0a\x03\x31\x32\x33"

# Use OrderedDict as a regular dict might get keys in different order every
# run, making the output not match
DOUBLE_KEY_IN = OrderedDict([("1", b"111"), ("4", b"222")])
DOUBLE_KEY_OUT = b"\x01\x03\x31\x31\x31\x04\x03\x32\x32\x32"

LARGE_KEY_IN = {"2": b"\x31" * 256}
LARGE_KEY_OUT = b"\x02\xff" + b"\x31" * 255 + b"\x02\x01\x31"


def test_write_single_key():
    assert write_tlv(SINGLE_KEY_IN) == SINGLE_KEY_OUT


def test_write_two_keys():
    assert write_tlv(DOUBLE_KEY_IN) == DOUBLE_KEY_OUT


def test_write_key_larger_than_255_bytes():
    # This will actually result in two serialized TLVs, one being 255 bytes
    # and the next one will contain the remaining one byte
    assert write_tlv(LARGE_KEY_IN) == LARGE_KEY_OUT


def test_read_single_key():
    assert read_tlv(SINGLE_KEY_OUT) == SINGLE_KEY_IN


def test_read_two_keys():
    assert read_tlv(DOUBLE_KEY_OUT) == DOUBLE_KEY_IN


def test_read_key_larger_than_255_bytes():
    assert read_tlv(LARGE_KEY_OUT) == LARGE_KEY_IN
