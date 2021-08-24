"""Unit tests for pyatv.support.http."""
import asyncio
import inspect
from typing import Optional, Tuple
from unittest.mock import MagicMock

from deepdiff import DeepDiff
import pytest

from pyatv import const
from pyatv.support.http import (
    AbstractHttpServerHandler,
    BasicHttpServer,
    HttpRequest,
    HttpResponse,
    HttpSession,
    HttpSimpleRouter,
    http_connect,
    http_server,
    parse_request,
    parse_response,
)

# HTTP MESSAGE PARSING
#
# Request and response share a lot of code, so most tests for response parsing cover
# request parsing as well.


def test_parse_response_ok_first_line():
    resp, rest = parse_response(b"HTTP/1.0 200 OK\r\n\r\n")
    assert resp.code == 200
    assert resp.message == "OK"
    assert rest == b""


def test_parse_response_missing_ending():
    with pytest.raises(ValueError) as exc:
        parse_response(b"HTTP/1.0 200 OK\r\n")

    assert "missing end lines" in str(exc)


def test_parse_response_headers():
    resp, rest = parse_response(b"HTTP/1.0 200 OK\r\nA: B\r\nC: D\r\n\r\n")
    assert len(resp.headers) == 2
    assert resp.headers["A"] == "B"
    assert resp.headers["C"] == "D"
    assert rest == b""


def test_parse_response_body():
    resp, rest = parse_response(b"HTTP/1.0 200 OK\r\nContent-Length: 4\r\n\r\nbody")
    assert resp.body == "body"
    assert rest == b""


def test_parse_response_too_no_body():
    content = b"HTTP/1.0 200 OK\r\nContent-Length: 5\r\n\r\n"
    resp, rest = parse_response(content)

    assert resp is None
    assert rest == content


def test_parse_response_too_short_body():
    content = b"HTTP/1.0 200 OK\r\nContent-Length: 5\r\n\r\nbody"
    resp, rest = parse_response(content)

    assert resp is None
    assert rest == content


def test_parse_response_body_excessive_data():
    resp, rest = parse_response(
        b"HTTP/1.0 200 OK\r\nContent-Length: 4\r\n\r\nbodyextra"
    )
    assert resp.body == "body"
    assert rest == b"extra"


def test_parse_response_sequent_messages():
    resp, rest = parse_response(
        b"HTTP/1.0 200 OK\r\nA: B\r\n\r\n"
        b"HTTP/1.0 200 OK\r\nContent-Length: 2\r\n\r\nAB"
        b"HTTP/1.0 200 OK\r\nContent-Length: 0\r\n\r\n"
    )
    assert resp.headers["A"] == "B"
    assert resp.body == ""

    resp, rest = parse_response(rest)
    assert resp.body == "AB"

    resp, rest = parse_response(rest)
    assert resp.headers["Content-Length"] == "0"
    assert resp.body == ""
    assert rest == b""


def test_parse_response_application_type_as_bytes():
    resp, rest = parse_response(
        b"HTTP/1.0 200 OK\r\nContent-Length: 4\r\n"
        + b"Content-Type: application/something\r\n\r\nbodyextra"
    )
    assert resp.body == b"body"
    assert rest == b"extra"


def test_parse_response_arbitrary_protocol_header():
    resp, _ = parse_response(b"FOO/3.14 200 OK\r\n\r\n")

    assert resp.protocol == "FOO"
    assert resp.version == "3.14"


def test_parse_response_ignore_header_case():
    resp, rest = parse_response(
        b"HTTP/1.0 200 OK\r\nCONTENT-lEnGtH: 4\r\n"
        + b"content-TYPE: application/something\r\n\r\nbodyextra"
    )
    assert resp.body == b"body"
    assert rest == b"extra"


def test_parse_request_ok_first_line():
    req, rest = parse_request(b"GET /test HTTP/1.0\r\n\r\n")
    assert req.method == "GET"
    assert req.path == "/test"
    assert req.protocol == "HTTP"
    assert req.version == "1.0"
    assert rest == b""


def test_parse_request_arbitrary_protocol_header():
    req, _ = parse_request(b"GET /test FOO/3.14\r\n\r\n")
    assert req.protocol == "FOO"
    assert req.version == "3.14"


def test_parse_request_method_with_underscore():
    req, _ = parse_request(b"SOME_METHOD /test FOO/3.14\r\n\r\n")
    assert req.method == "SOME_METHOD"


# BASIC HTTP SERVER


async def serve(handler) -> Tuple[asyncio.AbstractServer, int]:
    if inspect.isfunction(handler):
        mock = MagicMock()
        mock.handle_request = handler
        handler = mock

    return await http_server(lambda: BasicHttpServer(handler))


async def serve_and_connect(
    handler,
) -> Tuple[HttpSession, asyncio.AbstractServer]:
    server, port = await serve(handler)
    client = await http_connect("127.0.0.1", port)
    return client, server


async def test_server_request_unhandled_resource():
    client, server = await serve_and_connect(lambda req: False)

    resp = await client.get("/", allow_error=True)
    assert resp.protocol == "HTTP"
    assert resp.version == "1.1"
    assert resp.code == 404
    assert resp.message == "File not found"
    assert resp.headers["Server"]  # Don't care about value
    assert resp.body == "Not found"

    server.close()


async def test_server_request_single_file():
    def _handle_page(request: HttpRequest):
        assert request.protocol == "HTTP"
        assert request.version == "1.1"
        assert request.path == "/resource"
        assert request.method == "GET"

        return HttpResponse("HTTP", "1.1", 200, "OK", {"DummyHeader": "value"}, b"body")

    client, server = await serve_and_connect(_handle_page)

    resp = await client.get("/resource", allow_error=True)
    assert resp.protocol == "HTTP"
    assert resp.code == 200
    assert resp.message == "OK"
    assert DeepDiff(
        resp.headers,
        {
            "DummyHeader": "value",
            "Content-Length": 4,
            "Server": "pyatv-www/{const.__version__}",
        },
    )
    assert resp.body == "body"

    server.close()


async def test_server_bad_handler_gives_error():
    def _handle_page(request: HttpRequest):
        raise Exception("fail")

    client, server = await serve_and_connect(_handle_page)

    resp = await client.get("/", allow_error=True)
    assert resp.protocol == "HTTP"
    assert resp.code == 500
    assert resp.message == "Internal server error"
    assert resp.body == "fail"

    server.close()


class DummyRouter(HttpSimpleRouter):
    def __init__(self):
        super().__init__()
        self.add_route("GET", "/foo", self.foo)
        self.add_route("GET", "/bar", self.bar)

    def foo(self, request: HttpRequest) -> Optional[HttpResponse]:
        return HttpResponse("HTTP", "1.1", 200, "foo", {}, request.body)

    def bar(self, request: HttpRequest) -> Optional[HttpResponse]:
        return HttpResponse("HTTP", "1.1", 123, "dummy", {}, request.body)


async def test_simple_router():
    router = DummyRouter()
    resp = router.handle_request(
        HttpRequest("GET", "/foo", "HTTP", "1.1", {}, "foobar")
    )
    assert resp.code == 200
    assert resp.protocol == "HTTP"
    assert resp.version == "1.1"
    assert resp.body == "foobar"


async def test_simple_router_method():
    router = DummyRouter()
    resp = router.handle_request(
        HttpRequest("POST", "/foo", "HTTP", "1.1", {}, "foobar")
    )
    assert resp is None


async def test_server_with_router():
    client, server = await serve_and_connect(DummyRouter())

    resp = await client.get("/foo", allow_error=True)
    assert resp.code == 200

    server.close()


# HTTP CONNECTION


async def test_connection_send_processor():
    def send_processor(data: bytes) -> bytes:
        return data.replace(b"/foo", b"/bar")

    client, server = await serve_and_connect(DummyRouter())
    client.send_processor = send_processor

    resp = await client.get("/foo", allow_error=True)
    assert resp.code == 123
    assert resp.message == "dummy"

    server.close()


async def test_connection_receive_processor():
    def receive_processor(data: bytes) -> bytes:
        return data.replace(b"foo", b"something else")

    client, server = await serve_and_connect(DummyRouter())
    client.receive_processor = receive_processor

    resp = await client.get("/foo", allow_error=True)
    assert resp.code == 200
    assert resp.message == "something else"

    server.close()
