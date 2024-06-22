"""Unit tests for pyatv.support.http."""

import asyncio
import inspect
import logging
from typing import Optional, Tuple
from unittest.mock import MagicMock, patch

from deepdiff import DeepDiff
import pytest

from pyatv import exceptions
from pyatv.support.http import (
    SERVER_NAME,
    USER_AGENT,
    BasicHttpServer,
    HttpRequest,
    HttpResponse,
    HttpSession,
    HttpSimpleRouter,
    format_request,
    format_response,
    http_connect,
    http_server,
    parse_request,
    parse_response,
)
from pyatv.support.net import unused_port

_LOGGER = logging.getLogger(__name__)

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
    assert parse_response(b"HTTP/1.0 200 OK\r\n") == (None, b"HTTP/1.0 200 OK\r\n")


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


@pytest.mark.parametrize(
    "response,expected",
    [
        (
            HttpResponse("HTTP", "1.1", 200, "OK", {}, b""),
            f"HTTP/1.1 200 OK\r\nServer: {SERVER_NAME}\r\n\r\n".encode(),
        ),
        (
            HttpResponse("FOO", "3.14", 200, "OK", {}, b""),
            f"FOO/3.14 200 OK\r\nServer: {SERVER_NAME}\r\n\r\n".encode(),
        ),
        (
            HttpResponse("HTTP", "1.1", 404, "Not Found", {}, b""),
            f"HTTP/1.1 404 Not Found\r\nServer: {SERVER_NAME}\r\n\r\n".encode(),
        ),
        (
            HttpResponse("HTTP", "1.1", 200, "OK", {"A": "B"}, b""),
            f"HTTP/1.1 200 OK\r\nServer: {SERVER_NAME}\r\nA: B\r\n\r\n".encode(),
        ),
        (
            HttpResponse("HTTP", "1.1", 200, "OK", {}, b"test"),
            f"HTTP/1.1 200 OK\r\nServer: {SERVER_NAME}\r\nContent-Length: 4\r\n\r\ntest".encode(),
        ),
    ],
)
def test_format_response(response, expected):
    assert format_response(response) == expected


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


@pytest.mark.parametrize(
    "request_,expected",
    [
        (
            HttpRequest("GET", "/test", "HTTP", "1.1", {}, b""),
            f"GET /test HTTP/1.1\r\nUser-Agent: {USER_AGENT}\r\n\r\n".encode(),
        ),
        (
            HttpRequest("SOME METHOD", "/test", "HTTP", "1.1", {}, b""),
            f"SOME METHOD /test HTTP/1.1\r\nUser-Agent: {USER_AGENT}\r\n\r\n".encode(),
        ),
        (
            HttpRequest("GET", "/example", "HTTP", "1.1", {}, b""),
            f"GET /example HTTP/1.1\r\nUser-Agent: {USER_AGENT}\r\n\r\n".encode(),
        ),
        (
            HttpRequest("GET", "/test", "FOO", "3.14", {}, b""),
            f"GET /test FOO/3.14\r\nUser-Agent: {USER_AGENT}\r\n\r\n".encode(),
        ),
        (
            HttpRequest("GET", "/test", "HTTP", "1.1", {"A": "B"}, b""),
            f"GET /test HTTP/1.1\r\nUser-Agent: {USER_AGENT}\r\nA: B\r\n\r\n".encode(),
        ),
        (
            HttpRequest("GET", "/test", "HTTP", "1.1", {}, b"test"),
            f"GET /test HTTP/1.1\r\nUser-Agent: {USER_AGENT}\r\nContent-Length: 4\r\n\r\ntest".encode(),
        ),
    ],
)
def test_format_request(request_, expected):
    assert format_request(request_) == expected


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


@pytest.mark.asyncio
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


@pytest.mark.asyncio
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


@pytest.mark.asyncio
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


@pytest.mark.asyncio
async def test_simple_router():
    router = DummyRouter()
    resp = router.handle_request(
        HttpRequest("GET", "/foo", "HTTP", "1.1", {}, "foobar")
    )
    assert resp.code == 200
    assert resp.protocol == "HTTP"
    assert resp.version == "1.1"
    assert resp.body == "foobar"


@pytest.mark.asyncio
async def test_simple_router_method():
    router = DummyRouter()
    resp = router.handle_request(
        HttpRequest("POST", "/foo", "HTTP", "1.1", {}, "foobar")
    )
    assert resp is None


@pytest.mark.asyncio
async def test_server_with_router():
    client, server = await serve_and_connect(DummyRouter())

    resp = await client.get("/foo", allow_error=True)
    assert resp.code == 200

    server.close()


@pytest.mark.asyncio
async def test_server_process_received():
    client, server = await serve_and_connect(DummyRouter())

    with patch.object(BasicHttpServer, "process_received") as mock:
        mock.side_effect = lambda data: data.replace(b"/foo", b"/bar")
        resp = await client.get("/foo", allow_error=True)

    mock.assert_called_once()
    assert resp.code == 123

    server.close()


@pytest.mark.asyncio
async def test_server_process_sent():
    client, server = await serve_and_connect(DummyRouter())

    with patch.object(BasicHttpServer, "process_sent") as mock:
        mock.side_effect = lambda data: data.replace(b"200", b"456")
        resp = await client.get("/foo", allow_error=True)

    mock.assert_called_once()
    assert resp.code == 456

    server.close()


@pytest.mark.asyncio
async def test_server_async_handler():
    class TestRouter(HttpSimpleRouter):
        def __init__(self):
            super().__init__()
            self.add_route("GET", "/baz", self.baz)

        def baz(self, request):
            return asyncio.create_task(self.async_baz(request))

        async def async_baz(self, request):
            return HttpResponse("HTTP", "1.1", 200, "baz", {}, request.body)

    client, server = await serve_and_connect(TestRouter())

    resp = await client.get("/baz", allow_error=True)
    assert resp.code == 200
    assert resp.message == "baz"

    server.close()


@pytest.mark.asyncio
async def test_server_segmented_request():
    class TestHttpRequestConnection(asyncio.Protocol):
        def __init__(self) -> None:
            super().__init__()
            self.transport = None
            self.response_received = asyncio.Event()
            self.response_content = None

        def connection_made(self, transport):
            self.transport = transport

        def data_received(self, data):
            self.response_content = data
            self.response_received.set()

        async def send(self):
            self.response_received.clear()
            self.response_content = None

            data_received = asyncio.Event()
            original_data_received = BasicHttpServer.data_received

            # make sure the first chunk was received before sending the next
            def set_event_and_receive(self, data):
                data_received.set()
                return original_data_received(self, data)

            with patch.object(BasicHttpServer, "data_received", set_event_and_receive):
                self.transport.write(b"GET /foo HTTP/1.1\r\nContent-Length: 11\r\n\r\n")
                await data_received.wait()
                data_received.clear()
                self.transport.write(b"first")
                await data_received.wait()
                data_received.clear()
                self.transport.write(b"second")

            await self.response_received.wait()
            return self.response_content

    server, port = await serve(DummyRouter())
    loop = asyncio.get_event_loop()
    _, client = await loop.create_connection(
        TestHttpRequestConnection, "127.0.0.1", port
    )

    response = await client.send()
    assert response.startswith(b"HTTP/1.1 200 foo\r\n")
    assert response.endswith(b"\r\nfirstsecond")

    server.close()


# HTTP CONNECTION


@pytest.mark.asyncio
async def test_connection_send_processor():
    def send_processor(data: bytes) -> bytes:
        return data.replace(b"/foo", b"/bar")

    client, server = await serve_and_connect(DummyRouter())
    client.send_processor = send_processor

    resp = await client.get("/foo", allow_error=True)
    assert resp.code == 123
    assert resp.message == "dummy"

    server.close()


@pytest.mark.asyncio
async def test_connection_receive_processor():
    def receive_processor(data: bytes) -> bytes:
        return data.replace(b"foo", b"something else")

    client, server = await serve_and_connect(DummyRouter())
    client.receive_processor = receive_processor

    resp = await client.get("/foo", allow_error=True)
    assert resp.code == 200
    assert resp.message == "something else"

    server.close()


@pytest.mark.asyncio
async def test_connection_abort_timeout_if_connection_closed():
    # Set up a TCP server that will just consume the request and disconnect
    # so that the connection gets closed
    async def _dummy_server(reader, writer):
        _LOGGER.debug("Connection established")
        await reader.read(1)

        _LOGGER.debug("Data read, closing connection")
        writer.close()

    port = unused_port()
    await asyncio.start_server(_dummy_server, "127.0.0.1", port)

    connection = await http_connect("127.0.0.1", port)

    # Spawn three requests. Connection will be closed when processing the first one
    # but all three shall be aborted with an exception.
    tasks = [
        asyncio.create_task(connection.send_and_receive("GET", "/test"))
        for _ in range(3)
    ]
    for task in tasks:
        with pytest.raises(exceptions.ConnectionLostError):
            await task
