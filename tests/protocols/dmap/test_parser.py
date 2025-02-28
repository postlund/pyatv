"""Unit tests for pyatv.protocols.dmap.parser."""

import plistlib

import pytest

from pyatv import exceptions
from pyatv.protocols.dmap import parser, tags

TEST_TAGS = {
    "uuu8": parser.DmapTag(tags.read_uint, "uint8"),
    "uu16": parser.DmapTag(tags.read_uint, "uint16"),
    "uu32": parser.DmapTag(tags.read_uint, "uint32"),
    "uu64": parser.DmapTag(tags.read_uint, "uint64"),
    "bola": parser.DmapTag(tags.read_bool, "bool"),
    "bolb": parser.DmapTag(tags.read_bool, "bool"),
    "stra": parser.DmapTag(tags.read_str, "string"),
    "strb": parser.DmapTag(tags.read_str, "string"),
    "cona": parser.DmapTag("container", "container"),
    "conb": parser.DmapTag("container", "container 2"),
    "igno": parser.DmapTag(tags.read_ignore, "ignore"),
    "plst": parser.DmapTag(tags.read_bplist, "bplist"),
    "byte": parser.DmapTag(tags.read_bytes, "bytes"),
}


def lookup_tag(name):
    return TEST_TAGS[name]


def test_empty_data():
    assert parser.parse(b"", lookup_tag) == []


def test_parse_uint_of_various_lengths():
    in_data = (
        tags.uint8_tag("uuu8", 12)
        + tags.uint16_tag("uu16", 37888)
        + tags.uint32_tag("uu32", 305419896)
        + tags.uint64_tag("uu64", 8982983289232)
    )
    parsed = parser.parse(in_data, lookup_tag)
    assert 4 == len(parsed)
    assert 12 == parser.first(parsed, "uuu8")
    assert 37888 == parser.first(parsed, "uu16")
    assert 305419896 == parser.first(parsed, "uu32")
    assert 8982983289232 == parser.first(parsed, "uu64")


def test_parse_bool():
    in_data = tags.bool_tag("bola", True) + tags.bool_tag("bolb", False)
    parsed = parser.parse(in_data, lookup_tag)
    assert 2 == len(parsed)
    assert parser.first(parsed, "bola")
    assert not parser.first(parsed, "bolb")


def test_parse_strings():
    in_data = tags.string_tag("stra", "") + tags.string_tag("strb", "test string")
    parsed = parser.parse(in_data, lookup_tag)
    assert 2 == len(parsed)
    assert "" == parser.first(parsed, "stra")
    assert "test string" == parser.first(parsed, "strb")


def test_parse_binary_plist():
    data = {"key": "value"}
    in_data = tags.raw_tag("plst", plistlib.dumps(data, fmt=plistlib.FMT_BINARY))
    parsed = parser.parse(in_data, lookup_tag)
    assert 1 == len(parsed)
    assert data, parser.first(parsed, "plst")


def test_parse_bytes():
    in_data = tags.raw_tag("byte", b"\x01\xaa\xff\x45")
    parsed = parser.parse(in_data, lookup_tag)
    assert 1 == len(parsed)
    assert "0x01aaff45" == parser.first(parsed, "byte")


def test_parse_value_in_container():
    in_data = tags.container_tag(
        "cona", tags.uint8_tag("uuu8", 36) + tags.uint16_tag("uu16", 13000)
    )
    parsed = parser.parse(in_data, lookup_tag)
    assert 1 == len(parsed)
    inner = parser.first(parsed, "cona")
    assert 2 == len(inner)
    assert 36 == parser.first(inner, "uuu8")
    assert 13000 == parser.first(inner, "uu16")


def test_extract_simplified_container():
    elem = tags.uint8_tag("uuu8", 12)
    inner = tags.container_tag("conb", elem)
    in_data = tags.container_tag("cona", inner)
    parsed = parser.parse(in_data, lookup_tag)
    assert 12 == parser.first(parsed, "cona", "conb", "uuu8")


def test_ignore_value():
    elem = tags.uint8_tag("igno", 44)
    parsed = parser.parse(elem, lookup_tag)
    assert parser.first(parsed, "igno") is None


def test_simple_pprint():
    elem = tags.uint8_tag("uuu8", 12)
    inner = tags.container_tag("conb", elem)
    in_data = tags.container_tag("cona", inner)
    parsed = parser.parse(in_data, lookup_tag)
    assert (
        parser.pprint(parsed, lookup_tag) == "cona: [container, container]\n"
        "  conb: [container, container 2]\n"
        "    uuu8: 12 [uint, uint8]\n"
    )


def test_print_invalid_input_raises_exception():
    with pytest.raises(exceptions.InvalidDmapDataError):
        parser.pprint("bad data", lookup_tag)
