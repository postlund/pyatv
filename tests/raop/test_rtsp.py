"""Unit tests for pyatv.raop.rtsp."""

import pytest

from pyatv.raop.rtsp import parse_response


def test_parse_ok_first_line():
    resp, rest = parse_response("RTSP/1.0 200 OK\r\n\r\n")
    assert resp.code == 200
    assert resp.message == "OK"
    assert rest == ""


def test_parse_missing_ending():
    with pytest.raises(ValueError) as exc:
        parse_response("RTSP/1.0 200 OK\r\n")

    assert "missing end lines" in str(exc)


def test_parse_headers():
    resp, rest = parse_response("RTSP/1.0 200 OK\r\nA: B\r\nC: D\r\n\r\n")
    assert len(resp.headers) == 2
    assert resp.headers["A"] == "B"
    assert resp.headers["C"] == "D"
    assert rest == ""


def test_parse_body():
    resp, rest = parse_response("RTSP/1.0 200 OK\r\nContent-Length: 4\r\n\r\nbody")
    assert resp.body == "body"
    assert rest == ""


def test_parse_too_short_body():
    with pytest.raises(ValueError) as exc:
        parse_response("RTSP/1.0 200 OK\r\nContent-Length: 5\r\n\r\nbody")

    assert "too short body" in str(exc)


def test_parse_body_excessive_data():
    resp, rest = parse_response("RTSP/1.0 200 OK\r\nContent-Length: 4\r\n\r\nbodyextra")
    assert resp.body == "body"
    assert rest == "extra"


def test_parse_sequent_messages():
    resp, rest = parse_response(
        "RTSP/1.0 200 OK\r\nA: B\r\n\r\n"
        "RTSP/1.0 200 OK\r\nContent-Length: 2\r\n\r\nAB"
        "RTSP/1.0 200 OK\r\nContent-Length: 0\r\n\r\n"
    )
    assert resp.headers["A"] == "B"
    assert resp.body == ""

    resp, rest = parse_response(rest)
    assert resp.body == "AB"

    resp, rest = parse_response(rest)
    assert resp.headers["Content-Length"] == "0"
    assert resp.body == ""
    assert rest == ""
