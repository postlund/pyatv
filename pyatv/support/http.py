"""Module for working with HTTP requests."""
from abc import ABC, abstractmethod
import asyncio
from collections import deque
import logging
import pathlib
from queue import Queue
import re
from typing import Callable, Dict, Mapping, NamedTuple, Optional, Tuple, Union, cast

from aiohttp import ClientSession, web
from aiohttp.web import middleware

from pyatv import const, exceptions
from pyatv.support import log_binary
from pyatv.support.collections import CaseInsensitiveDict
from pyatv.support.net import unused_port

_LOGGER = logging.getLogger(__name__)

USER_AGENT = f"pyatv/{const.__version__}"
SERVER_NAME = f"pyatv-www/{const.__version__}"

# This timeout is rather long and that is for a reason. If a device is sleeping, it
# automatically wakes up when a service is requested from it. Up to 20 seconds or so
# have been seen. So to deal with that, keep this high.
DEFAULT_TIMEOUT = 25.0  # Seconds

# Used for pre/post processing in HTTP
DataProcessor = Callable[[bytes], bytes]


def _null_processor(data: bytes) -> bytes:
    """Data processor not doing any processing (just returning data)."""
    return data


def _format_message(
    method: str,
    uri: str,
    protocol: str = "HTTP/1.1",
    user_agent: str = USER_AGENT,
    content_type: Optional[str] = None,
    headers: Optional[Mapping[str, object]] = None,
    body: Optional[Union[str, bytes]] = None,
) -> bytes:
    if isinstance(body, str):
        body = body.encode("utf-8")

    msg = f"{method} {uri} {protocol}"
    if "User-Agent" not in (headers or {}):
        msg += f"\r\nUser-Agent: {user_agent}"
    if content_type:
        msg += f"\r\nContent-Type: {content_type}"
    if body:
        msg += f"\r\nContent-Length: {len(body) if body else 0}"

    for key, value in (headers or {}).items():
        msg += f"\r\n{key}: {value}"
    msg += 2 * "\r\n"

    output = msg.encode("utf-8")
    if body:
        output += body

    return output


class HttpResponse(NamedTuple):
    """Generic HTTP response message."""

    protocol: str
    version: str
    code: int
    message: str
    headers: Mapping[str, str]
    body: Union[str, bytes]


class HttpRequest(NamedTuple):
    """Generic HTTP request message."""

    method: str
    path: str
    protocol: str
    version: str
    headers: Mapping[str, str]
    body: Union[str, bytes]


def _key_value(line: str) -> Tuple[str, str]:
    split = line.split(": ", maxsplit=1)
    return split[0], split[1]


def _parse_http_message(
    message: bytes,
) -> Tuple[Optional[str], CaseInsensitiveDict[str], Union[bytes, str], bytes]:
    """Parse HTTP response."""
    try:
        header_str, body = message.split(b"\r\n\r\n", maxsplit=1)
    except ValueError as ex:
        raise ValueError("missing end lines") from ex
    headers = header_str.decode("utf-8").split("\r\n")

    msg_headers = CaseInsensitiveDict(_key_value(line) for line in headers[1:] if line)

    # TODO: pylint on python 3.6 does not seem to find CaseInsensitiveDict.get, but
    # other versions seems to work fine. Remove this ignore when python 3.6 is dropped.
    content_length = int(
        msg_headers.get("Content-Length", 0)  # pylint: disable=no-member
    )
    if len(body or []) < content_length:
        return None, CaseInsensitiveDict(), b"", message

    msg_body: Union[str, bytes] = body[0:content_length]

    # Assume body is text unless content type is application/octet-stream
    # TODO: Remove pylint disable when python 3.6 is dropped
    if not msg_headers.get("Content-Type", "").startswith(  # pylint: disable=no-member
        "application"
    ):
        msg_body = cast(bytes, msg_body).decode("utf-8")  # We know it's bytes here

    return (
        headers[0],
        msg_headers,
        msg_body,
        body[content_length:],
    )


def parse_response(response: bytes) -> Tuple[Optional[HttpResponse], bytes]:
    """Parse HTTP response."""
    first_line, msg_headers, msg_body, rest = _parse_http_message(response)
    if not first_line:
        return None, rest

    # <method> <path> <protocol>/<version
    # E.g. GET / HTTP/1.1
    match = re.match(r"([^/]+)/([0-9.]+) ([0-9]+) (.*)", first_line)
    if not match:
        raise ValueError(f"bad first line: {first_line}")

    protocol, version, code, message = match.groups()

    return (
        HttpResponse(protocol, version, int(code), message, msg_headers, msg_body),
        rest,
    )


def parse_request(request: bytes) -> Tuple[Optional[HttpRequest], bytes]:
    """Parse HTTP request."""
    first_line, msg_headers, msg_body, rest = _parse_http_message(request)
    if not first_line:
        return None, rest

    # <method> <path> <protocol>/<version>
    # E.g. GET / HTTP/1.1
    match = re.match(r"([A-Z_]+) ([^ ]+) ([^/]+)/([0-9.]+)", first_line)
    if not match:
        raise ValueError(f"bad first line: {first_line}")

    method, path, protocol, version = match.groups()

    return (
        HttpRequest(method, path, protocol, version, msg_headers, msg_body),
        rest,
    )


class ClientSessionManager:
    """Manages an aiohttp ClientSession instance."""

    def __init__(self, session: ClientSession, should_close: bool) -> None:
        """Initialize a new ClientSessionManager."""
        self._session = session
        self._should_close = should_close

    @property
    def session(self) -> ClientSession:
        """Return client session."""
        return self._session

    async def close(self) -> None:
        """Close session."""
        if self._should_close:
            await self.session.close()


class HttpSession:
    """This class simplifies GET/POST requests."""

    def __init__(self, client_session: ClientSession, base_url: str) -> None:
        """Initialize a new HttpSession."""
        self._session = client_session
        self.base_url = base_url

    async def get_data(
        self,
        path: str,
        headers: Mapping[str, object] = None,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> Tuple[bytes, int]:
        """Perform a GET request."""
        url = self.base_url + path
        _LOGGER.debug("GET URL: %s", url)
        resp = None
        try:
            resp = await self._session.get(url, headers=headers, timeout=timeout)
            _LOGGER.debug(
                "Response: status=%d, headers=[%s]", resp.status, resp.headers
            )
            if resp.content_length is not None:
                resp_data = await resp.read()
                log_binary(_LOGGER, "<< GET", Data=resp_data)
            else:
                resp_data = b""
            return resp_data, resp.status
        except Exception:
            if resp is not None:
                resp.close()
            raise
        finally:
            if resp is not None:
                await resp.release()

    async def post_data(
        self,
        path: str,
        data: bytes = None,
        headers: Mapping[str, object] = None,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> Tuple[bytes, int]:
        """Perform a POST request."""
        url = self.base_url + path
        _LOGGER.debug("POST URL: %s", url)
        log_binary(_LOGGER, ">> POST", Data=data)

        resp = None
        try:
            resp = await self._session.post(
                url,
                headers=headers,
                data=data,
                timeout=timeout,
            )
            _LOGGER.debug(
                "Response: status=%d, headers=[%s]", resp.status, resp.headers
            )
            if resp.content_length is not None:
                resp_data = await resp.read()
                log_binary(_LOGGER, "<< POST", Data=resp_data)
            else:
                resp_data = b""
            return resp_data, resp.status
        except Exception as ex:
            if resp is not None:
                resp.close()
            raise ex
        finally:
            if resp is not None:
                await resp.release()


class HttpConnection(asyncio.Protocol):
    """Representation of a HTTP connection."""

    def __init__(
        self,
        receive_processor: Optional[Callable[[bytes], bytes]] = None,
        send_processor: Optional[Callable[[bytes], bytes]] = None,
    ) -> None:
        """Initialize a new ."""
        self.transport: Optional[asyncio.Transport] = None
        self.receive_processor: Callable[[bytes], bytes] = (
            receive_processor or _null_processor
        )
        self.send_processor: Callable[[bytes], bytes] = (
            send_processor or _null_processor
        )
        self._local_ip: Optional[str] = None
        self._remote_ip: Optional[str] = None
        self._requests: deque = deque()
        self._responses: Queue = Queue()
        self._buffer = b""

    @property
    def local_ip(self) -> str:
        """Return IP address of local interface."""
        if self._local_ip is None:
            raise RuntimeError("not connected")
        return self._local_ip

    @property
    def remote_ip(self) -> str:
        """Return IP address of remote instance."""
        if self._remote_ip is None:
            raise RuntimeError("not connected")
        return self._remote_ip

    def close(self) -> None:
        """Close HTTP connection."""
        if self.transport:
            transport = self.transport
            self.transport = None
            transport.close()

    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        """Handle that a connection has been made."""
        self.transport = cast(asyncio.Transport, transport)
        sock = self.transport.get_extra_info("socket")
        self._local_ip = sock.getsockname()[0]
        self._remote_ip = sock.getpeername()[0]
        _LOGGER.debug("Connected to %s", self.remote_ip)

    def data_received(self, data: bytes) -> None:
        """Handle incoming HTTP data."""
        data = self.receive_processor(data)

        _LOGGER.debug("Received: %s", data)
        self._buffer += data
        while self._buffer:
            # Try to parse a complete response
            parsed, self._buffer = parse_response(self._buffer)
            if parsed is None:
                _LOGGER.debug("Not enough data to decode message")
                break

            # Dispatch message to first receiver
            self._responses.put(parsed)
            if self._requests:
                self._requests.pop().set()
            else:
                _LOGGER.warning("Got response without having a request: %s", parsed)

    @staticmethod
    def error_received(exc) -> None:
        """Handle a connection error."""
        _LOGGER.error("Error received: %s", exc)

    def connection_lost(self, exc) -> None:
        """Handle that connection was lost."""
        _LOGGER.debug("Connection closed")

    async def get(self, path: str, allow_error: bool = False) -> HttpResponse:
        """Make a GET request and return response."""
        return await self.send_and_receive("GET", path, allow_error=allow_error)

    async def post(
        self,
        path: str,
        headers: Optional[Mapping[str, object]] = None,
        body: Optional[Union[str, bytes]] = None,
        allow_error: bool = False,
    ) -> HttpResponse:
        """Make a POST request and return response."""
        return await self.send_and_receive(
            "POST", path, headers=headers, body=body, allow_error=allow_error
        )

    async def send_and_receive(
        self,
        method: str,
        uri: str,
        protocol: str = "HTTP/1.1",
        user_agent: str = USER_AGENT,
        content_type: Optional[str] = None,
        headers: Optional[Mapping[str, object]] = None,
        body: Optional[Union[str, bytes]] = None,
        allow_error: bool = False,
    ) -> HttpResponse:
        """Send a HTTP message and return response."""
        output = _format_message(
            method, uri, protocol, user_agent, content_type, headers, body
        )

        _LOGGER.debug("Sending %s message: %s", protocol, output)
        if not self.transport:
            raise RuntimeError("not connected to remote")

        self.transport.write(self.send_processor(output))

        event = asyncio.Event()
        self._requests.appendleft(event)
        try:
            await asyncio.wait_for(event.wait(), timeout=4)
            response = cast(HttpResponse, self._responses.get())
        except asyncio.TimeoutError as ex:
            raise TimeoutError(f"no response to {method} {uri} ({protocol})") from ex
        finally:
            # If request failed and event is still in request queue, remove it
            if self._requests and self._requests[-1] == event:
                self._requests.pop()

        _LOGGER.debug("Got %s response: %s:", response.protocol, response)

        if response.code == 403:
            raise exceptions.AuthenticationError("not authenticated")

        # Password required
        if response.code == 401:
            if allow_error:
                return response
            raise exceptions.AuthenticationError("not authenticated")

        # Positive response
        if 200 <= response.code < 300 or allow_error:
            return response

        raise exceptions.HttpError(
            f"{protocol} method {method} failed with code "
            f"{response.code}: {response.message}",
            response.code,
        )


class AbstractHttpServerHandler(ABC):
    """Abstract base class for handling HTTP requests."""

    @abstractmethod
    def handle_request(self, request: HttpRequest) -> Optional[HttpResponse]:
        """Handle incoming request and return response."""


class HttpSimpleRouter(AbstractHttpServerHandler):
    """Simple router that routes method and path to handler function."""

    def __init__(self):
        """Initialize a new HttpSimpleRouter instance."""
        super().__init__()
        # method -> path -> handler
        self._routes: Dict[str, Dict[str, Callable[[HttpRequest], None]]] = {}

    def add_route(
        self, method: str, path: str, target: Callable[[HttpRequest], None]
    ) -> None:
        """Add new handler to route."""
        self._routes.setdefault(method, {})[path] = target

    def handle_request(self, request: HttpRequest) -> Optional[HttpResponse]:
        """Dispatch request to correct handler method."""
        for path, target in self._routes.get(request.method, {}).items():
            if re.match(path, request.path):
                return target(request)
        return None


class BasicHttpServer(asyncio.Protocol):
    """Super basic HTTP server." """

    def __init__(self, handler: AbstractHttpServerHandler) -> None:
        """Initialize a new BasicHttpServer instance."""
        self.handler: AbstractHttpServerHandler = handler
        self.transport = None

    def connection_made(self, transport):
        """Handle that a connection has been made."""
        _LOGGER.debug("Connection from %s", transport.get_extra_info("peername"))
        self.transport = transport

    def data_received(self, data: bytes):
        """Handle incoming HTTP request."""
        _LOGGER.debug("Received: %s", data)

        # Process all requests in packet
        while data:
            data = self._parse_and_send_next(data)

    def _parse_and_send_next(self, data: bytes):
        resp: Optional[HttpResponse] = None
        rest: bytes = b""
        try:
            request, rest = parse_request(data)

            # TODO: If no request could be parsed, then there's not enough data.
            # Segmented requests (over several IP packets) are currently not
            # implemented. Implement this when needed.
            if not request:
                raise exceptions.NotSupportedError(
                    "segmented HTTP requests not supported"
                )

            resp = self.handler.handle_request(request)
        except Exception as ex:
            _LOGGER.exception("failed to process request")
            resp = HttpResponse(
                "HTTP", "1.1", 500, "Internal server error", {}, str(ex)
            )

        if not resp:
            resp = HttpResponse("HTTP", "1.1", 404, "File not found", {}, "Not found")

        response = f"{resp.protocol}/{resp.version} {resp.code} {resp.message}\r\n"
        response += f"Server: {SERVER_NAME}\r\n"
        for key, value in resp.headers.items():
            response += f"{key}: {value}\r\n"

        body = resp.body or b""
        if body:
            body = body.encode("utf-8") if isinstance(body, str) else body
            response += f"Content-Length: {len(body)}\r\n"

        if self.transport:
            self.transport.write(response.encode("utf-8") + b"\r\n" + body)

        return rest


class StaticFileWebServer:
    """Web server serving only a single file."""

    def __init__(self, file_to_serve: str, address: str, port: Optional[int] = None):
        """Initialize a new StaticFileWebServer."""
        self.path = pathlib.Path(file_to_serve)
        self.app = web.Application(middlewares=[self._middleware])
        self.app.router.add_static("/", self.path.parent, show_index=False)
        self.runner = web.AppRunner(self.app)
        self.site: Optional[web.TCPSite] = None
        self._address = address  # Local address to bind to
        self._port = port

    async def start(self) -> None:
        """Start the web server."""
        if not self._port:
            self._port = unused_port()

        _LOGGER.debug("Starting AirPlay file server on port %d", self._port)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, str(self._address), self._port)
        await self.site.start()  # type: ignore

    async def close(self) -> None:
        """Stop the web server and free resources."""
        _LOGGER.debug("Closing local AirPlay web server")
        await self.runner.cleanup()

    @property
    def file_address(self) -> str:
        """Address to the file being served."""
        return f"http://{self._address}:{self._port}/{self.path.name}"

    # This middleware makes sure only the specified file is accessible. This is needed
    # since aiohttp only supports serving an entire directory.
    @middleware
    async def _middleware(self, request, handler):
        if request.rel_url.path == f"/{self.path.name}":
            return await handler(request)
        return web.Response(body="Permission denied", status=401)


async def http_connect(address: str, port: int) -> HttpConnection:
    """Open connection to a remote host."""
    loop = asyncio.get_event_loop()
    _, connection = await loop.create_connection(HttpConnection, address, port)
    return cast(HttpConnection, connection)


async def http_server(
    server_factory: Callable[[], BasicHttpServer],
    address: str = "127.0.0.1",
    port: int = 0,
) -> Tuple[asyncio.AbstractServer, int]:
    """Set up a new basic HTTP server."""
    loop = asyncio.get_event_loop()
    server = await loop.create_server(server_factory, address, port)
    if server.sockets is None:
        raise RuntimeError("failed to set up http server")
    return server, server.sockets[0].getsockname()[1]


async def create_session(
    session: Optional[ClientSession] = None,
) -> ClientSessionManager:
    """Create aiohttp ClientSession manged by pyatv."""
    return ClientSessionManager(session or ClientSession(), session is None)
