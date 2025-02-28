"""Unit tests for pyatv.support.dns"""

import io
import typing

import pytest

from pyatv.support import dns


@pytest.mark.parametrize(
    "name,expected",
    (
        ("_http._tcp.local", (None, "_http._tcp", "local")),
        ("foo._http._tcp.local", ("foo", "_http._tcp", "local")),
        ("foo.bar._http._tcp.local", ("foo.bar", "_http._tcp", "local")),
    ),
    ids=("ptr", "no_dot", "with_dot"),
)
def test_happy_service_instance_names(name, expected):
    assert dns.ServiceInstanceName.split_name(name) == expected


@pytest.mark.parametrize(
    "name",
    (
        "_http.local",
        "._tcp.local",
        "_http.foo._tcp.local",
        "_tcp._http.local",
    ),
    ids=("no_proto", "no_service", "split", "reversed"),
)
def test_sad_service_instance_names(name):
    with pytest.raises(ValueError):
        dns.ServiceInstanceName.split_name(name)


# mapping is test_id: tuple(name, expected_raw)
encode_domain_names = {
    "root": (".", b"\x00"),
    "empty": ("", b"\x00"),
    "example.com": ("example.com", b"\x07example\x03com\x00"),
    "example.com_list": (["example", "com"], b"\x07example\x03com\x00"),
    "unicode": ("Bücher.example", b"\x07B\xc3\xbccher\x07example\x00"),
    "dotted_instance": (
        "Dot.Within._http._tcp.example.local",
        b"\x0aDot.Within\x05_http\x04_tcp\x07example\x05local\x00",
    ),
    "dotted_instance_list": (
        ["Dot.Within", "_http", "_tcp", "example", "local"],
        b"\x0aDot.Within\x05_http\x04_tcp\x07example\x05local\x00",
    ),
    "truncated_ascii": (
        (
            "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
            "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
            ".test"
        ),
        (
            b"\x3fabcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijk"
            b"\x04test"
            b"\x00"
        ),
    ),
    "truncated_unicode": (
        (
            # The 'a' is at the beginning to force the codepoints to be split at 63
            # bytes. The next line is also at the right length to be below 88 characters
            # even if each kana is counted as a double-width character. Additionally,
            # this sequence is NF*D* normalized, not NFC (which is what is used for
            # Net-Unicode).
            "aがあいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめも"
            ".test"
        ),
        (
            b"\x3d"
            b"a\xe3\x81\x8c\xe3\x81\x82\xe3\x81\x84\xe3\x81\x86\xe3\x81\x88\xe3\x81\x8a"
            b"\xe3\x81\x8b\xe3\x81\x8d\xe3\x81\x8f\xe3\x81\x91\xe3\x81\x93\xe3\x81\x95"
            b"\xe3\x81\x97\xe3\x81\x99\xe3\x81\x9b\xe3\x81\x9d\xe3\x81\x9f\xe3\x81\xa1"
            b"\xe3\x81\xa4\xe3\x81\xa6"
            b"\x04test"
            b"\x00"
        ),
    ),
}


@pytest.mark.parametrize(
    "name,expected_raw",
    [pytest.param(*value, id=key) for key, value in encode_domain_names.items()],
)
def test_qname_encode(name, expected_raw):
    assert dns.qname_encode(name) == expected_raw


# mapping is test_id: tuple(raw_name, offset, expected_name, expected_offset)
# If expected offset is None, it means len(raw_name), otherwise it's like an array index
# (positive is from the beginning, negative from the end)
decode_domain_names = {
    "simple": (b"\x03foo\x07example\x03com\x00", 0, "foo.example.com", None),
    "null": (b"\00", 0, "", None),
    "compressed": (b"aaaa\x04test\x00\x05label\xc0\x04\xab\xcd", 10, "label.test", -2),
    # This case has two levels of compression
    "multi_compressed": (
        b"aaaa\x04test\x00\x05label\xc0\x04\x03foo\xc0\x0a\xab\xcd",
        18,
        "foo.label.test",
        -2,
    ),
    # Taken straight from the Internationalized Domain name Wikipedia page
    "idna": (b"\x0dxn--bcher-kva\x07example\x00", 0, "bücher.example", None),
    # Taken from issue #919. Apple puts a non-breaking space between "Apple" and "TV".
    "nbsp": (
        b"\x10Apple\xc2\xa0TV (4167)\x05local\x00",
        0,
        "Apple\xa0TV (4167).local",
        None,
    ),
    # This is a doozy of a test case; it's covering a couple different areas of Unicode,
    # as well as exercising that DNS-SD allows dots in instance names.
    "unicode": (
        (
            b"\x1d\xe5\xb1\x85\xe9\x96\x93 Apple\xc2\xa0TV. En Espa\xc3\xb1ol"
            b"\x05local"
            b"\x00"
        ),
        0,
        "居間 Apple TV. En Español.local",
        None,
    ),
}


@pytest.mark.parametrize(
    "raw_name,offset,expected_name,expected_offset",
    [pytest.param(*value, id=key) for key, value in decode_domain_names.items()],
)
def test_domain_name_parsing(
    raw_name: bytes,
    offset: int,
    expected_name: str,
    expected_offset: typing.Optional[int],
):
    with io.BytesIO(raw_name) as buffer:
        buffer.seek(offset)
        name = dns.parse_domain_name(buffer)
        assert name == expected_name
        if expected_offset is None:
            assert buffer.tell() == len(raw_name)
        else:
            # if expected_offset is positive, this will wrap around to the beginning, if
            # it's negative it won't.
            raw_len = len(raw_name)
            assert buffer.tell() == (raw_len + expected_offset) % raw_len


# mapping is test_id: tuple(encoded_data, expected_data, expected_offset)
# If expected offset is None, it means len(raw_name), otherwise it's like an array index
# (positive is from the beginning, negative from the end)
decode_strings = {
    "null": (b"\x00", b"", None),
    # 63 is significant because that's the max length for a domain label, but not a
    # character-string (they have similar encodings).
    "len_63": (b"\x3f" + (63 * b"0"), (63 * b"0"), None),
    # For similar reasons as 63, 64 is significant because it would set only one of the
    # flag bits for name compression if domain-name encoding is assumed.
    "len_64": (b"\x40" + (64 * b"0"), (64 * b"0"), None),
    # Ditto for 128, but the other flag
    "len_128": (b"\x80" + (128 * b"0"), (128 * b"0"), None),
    # ...and 192 is both flags
    "len_192": (b"\xc0" + (192 * b"0"), (192 * b"0"), None),
    # 255 is the max length a character-string can be
    "len_255": (b"\xff" + (255 * b"0"), (255 * b"0"), None),
    "trailing": (b"\x0a" + (10 * b"2") + (17 * b"9"), (10 * b"2"), -17),
}


@pytest.mark.parametrize(
    "encoded_data,expected_data,expected_offset",
    [pytest.param(*value, id=key) for key, value in decode_strings.items()],
)
def test_string_parsing(
    encoded_data: bytes,
    expected_data: bytes,
    expected_offset: typing.Optional[int],
):
    with io.BytesIO(encoded_data) as buffer:
        name = dns.parse_string(buffer)
        assert name == expected_data
        if expected_offset is None:
            assert buffer.tell() == len(encoded_data)
        else:
            # if expected_offset is positive, this will wrap around to the beginning, if
            # it's negative it won't.
            data_len = len(encoded_data)
            assert buffer.tell() == (data_len + expected_offset) % data_len


def test_dns_sd_txt_parse_single():
    """Test that a TXT RDATA section with one key can be parsed properly."""
    data = b"\x07foo=bar"
    extra_data = data + b"\xde\xad\xbe\xef" * 3
    with io.BytesIO(extra_data) as buffer:
        txt_dict = dns.parse_txt_dict(buffer, len(data))
        assert buffer.tell() == len(data)
        assert txt_dict == {"foo": b"bar"}


def test_dns_sd_txt_parse_multiple():
    """Test that a TXT RDATA section with multiple keys can be parsed properly."""
    data = b"\x07foo=bar\x09spam=eggs"
    extra_data = data + b"\xde\xad\xbe\xef" * 2
    with io.BytesIO(extra_data) as buffer:
        txt_dict = dns.parse_txt_dict(buffer, len(data))
        assert buffer.tell() == len(data)
        assert txt_dict == {"foo": b"bar", "spam": b"eggs"}


def test_dns_sd_txt_parse_binary():
    """Test that a TXT RDATA section with a binary value can be parsed properly."""
    # 0xfeed can't be decoded as UTF-8 or ASCII, so it'll thrown an error if it's not
    # being treated as binary data.
    data = b"\x06foo=\xfe\xed"
    extra_data = data + b"\xde\xad\xbe\xef" * 3
    with io.BytesIO(extra_data) as buffer:
        txt_dict = dns.parse_txt_dict(buffer, len(data))
        assert buffer.tell() == len(data)
        assert txt_dict == {"foo": b"\xfe\xed"}


def test_dns_sd_txt_parse_long():
    """Test that a TXT RDATA section with a long value can be parsed properly."""
    # If TXT records are being parsed the same way domain names are, this won't work as
    # the data is too long to fit in a label.
    data = b"\xccfoo=" + b"\xca\xfe" * 100
    extra_data = data + b"\xde\xad\xbe\xef" * 3
    with io.BytesIO(extra_data) as buffer:
        txt_dict = dns.parse_txt_dict(buffer, len(data))
        assert buffer.tell() == len(data)
        assert txt_dict == {"foo": b"\xca\xfe" * 100}


@pytest.mark.parametrize(
    "data,expected",
    [
        ({"foo": b"bar"}, b"\x07foo=bar"),
        ({b"foo": "bar"}, b"\x07foo=bar"),
        ({"foo": "bar", "spam": "eggs"}, b"\x07foo=bar\x09spam=eggs"),
    ],
)
def test_dns_sd_txt_format(data, expected):
    assert dns.format_txt_dict(data) == expected


@pytest.mark.parametrize(
    "record_type,data,expected",
    [
        (dns.QueryType.A, b"\x0a\x00\x00\x2a", "10.0.0.42"),
        (dns.QueryType.PTR, b"\x03foo\x07example\x03com\x00", "foo.example.com"),
        (dns.QueryType.TXT, b"\x07foo=bar", {"foo": b"bar"}),
        (
            dns.QueryType.SRV,
            b"\x00\x0a\x00\x00\x00\x50\x03foo\x07example\x03com\x00",
            {
                "priority": 10,
                "weight": 0,
                "port": 80,
                "target": "foo.example.com",
            },
        ),
    ],
    # Use the name of the record type as the test id
    ids=(
        t.name
        for t in (
            dns.QueryType.A,
            dns.QueryType.PTR,
            dns.QueryType.TXT,
            dns.QueryType.SRV,
        )
    ),
)
def test_parse_rdata(
    record_type: dns.QueryType,
    data: bytes,
    expected: typing.Any,
):
    with io.BytesIO(data) as buffer:
        assert record_type.parse_rdata(buffer, len(data)) == expected
        assert buffer.tell() == len(data)
