"""Unit tests for pyatv.support.hap_tlv8."""

from collections import OrderedDict

from pyatv.auth.hap_tlv8 import (
    ErrorCode,
    Method,
    State,
    TlvValue,
    read_tlv,
    stringify,
    write_tlv,
)

SINGLE_KEY_IN = {10: b"123"}
SINGLE_KEY_OUT = b"\x0a\x03\x31\x32\x33"

# Use OrderedDict as a regular dict might get keys in different order every
# run, making the output not match
DOUBLE_KEY_IN = OrderedDict([(1, b"111"), (4, b"222")])
DOUBLE_KEY_OUT = b"\x01\x03\x31\x31\x31\x04\x03\x32\x32\x32"

LARGE_KEY_IN = {2: b"\x31" * 256}
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


def test_stringify_method():
    assert stringify({TlvValue.Method: b"\x00"}) == "Method=PairSetup"
    assert stringify({TlvValue.Method: b"\x02"}) == "Method=PairVerify"


def test_stringify_seqno():
    assert stringify({TlvValue.SeqNo: b"\x01"}) == "SeqNo=M1"
    assert stringify({TlvValue.SeqNo: b"\x02"}) == "SeqNo=M2"
    assert stringify({TlvValue.SeqNo: b"\x03"}) == "SeqNo=M3"
    assert stringify({TlvValue.SeqNo: b"\x04"}) == "SeqNo=M4"
    assert stringify({TlvValue.SeqNo: b"\x05"}) == "SeqNo=M5"
    assert stringify({TlvValue.SeqNo: b"\x06"}) == "SeqNo=M6"


def test_stringify_error():
    assert stringify({TlvValue.Error: b"\x02"}) == "Error=Authentication"
    assert stringify({TlvValue.Error: b"\x05"}) == "Error=MaxTries"


def test_stringify_backoff():
    assert stringify({TlvValue.BackOff: b"\x02\x00"}) == "BackOff=2s"


def test_stringify_remainging_short():
    values = [
        TlvValue.Identifier,
        TlvValue.Salt,
        TlvValue.PublicKey,
        TlvValue.Proof,
        TlvValue.EncryptedData,
        TlvValue.Certificate,
        TlvValue.Signature,
        TlvValue.Permissions,
        TlvValue.FragmentData,
        TlvValue.FragmentLast,
    ]

    for value in values:
        assert stringify({value: b"\x00\x01\x02\x03"}) == f"{value.name}=4bytes"


def test_stringify_multiple():
    assert (
        stringify(
            {
                TlvValue.Method: b"\x00",
                TlvValue.SeqNo: b"\x01",
                TlvValue.Error: b"\x03",
                TlvValue.BackOff: b"\x01\x00",
            }
        )
        == "Method=PairSetup, SeqNo=M1, Error=BackOff, BackOff=1s"
    )


def test_stringify_unknown_values():
    assert (
        stringify(
            {
                TlvValue.Method: b"\xAA",
                TlvValue.SeqNo: b"\xAB",
                TlvValue.Error: b"\xAC",
                0xAD: b"\x01\x02\x03",
            }
        )
        == "Method=0xaa, SeqNo=0xab, Error=0xac, 0xad=3bytes"
    )
