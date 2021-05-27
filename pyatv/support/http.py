"""Module for working with HTTP requests."""
import re
from typing import Mapping, NamedTuple, Optional, Tuple, Union, cast


class HttpResponse(NamedTuple):
    """Generic HTTP response message."""

    protocol: str
    version: str
    code: int
    message: str
    headers: Mapping[str, str]
    body: Union[str, bytes]


def _key_value(line: str) -> Tuple[str, str]:
    split = line.split(": ", maxsplit=1)
    return split[0], split[1]


def parse_message(response: bytes) -> Tuple[Optional[HttpResponse], bytes]:
    """Parse HTTP response."""
    try:
        header_str, body = response.split(b"\r\n\r\n", maxsplit=1)
    except ValueError as ex:
        raise ValueError("missing end lines") from ex
    headers = header_str.decode("utf-8").split("\r\n")

    # <protocol>/<version> <status code> <message>
    # E.g. HTTP/1.0 200 OK
    match = re.match(r"([^/]+)/([0-9.]+) (\d+) (.+)", headers[0])
    if not match:
        raise ValueError(f"bad first line: {headers[0]}")

    protocol, version, code, message = match.groups()
    resp_headers = dict(_key_value(line) for line in headers[1:] if line)

    content_length = int(resp_headers.get("Content-Length", 0))
    if len(body or []) < content_length:
        return None, response

    response_body: Union[str, bytes] = body[0:content_length]

    # Assume body is text unless content type is application/octet-stream
    if resp_headers.get("Content-Type") != "application/octet-stream":
        # We know it's bytes here
        response_body = cast(bytes, response_body).decode("utf-8")

    return (
        HttpResponse(
            protocol, version, int(code), message, resp_headers, response_body
        ),
        body[content_length:],
    )
