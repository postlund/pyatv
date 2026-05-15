"""Tests for pyatv.protocols.raop.audio_source.

Includes a regression test for #2849: streaming a media file larger than
PatchedIceCastClient's internal BUFFER_SIZE must not deadlock during
miniaudio's decoder init.
"""

import pytest
from pytest_httpserver import HTTPServer

from pyatv.protocols.raop.audio_source import (
    BUFFER_SIZE,
    InternetSource,
)

from tests.utils import data_path

pytestmark = pytest.mark.asyncio

SHORT_FIXTURE = "static_3sec.ogg"  # existing, ~4 KiB
LONG_FIXTURE = "audio_long.mp3"  # new, just over BUFFER_SIZE


async def _serve_and_open(httpserver: HTTPServer, body: bytes, name: str) -> None:
    httpserver.expect_request("/" + name).respond_with_data(
        body, content_type="application/octet-stream"
    )
    url = httpserver.url_for("/" + name)
    src = await InternetSource.open(url, sample_rate=44100, channels=2, sample_size=2)
    try:
        frames = await src.readframes(352)
        assert frames, "InternetSource returned no audio frames after init"
    finally:
        await src.close()


async def test_internet_source_short_stream(httpserver: HTTPServer):
    """Streaming a small file over HTTP works (fast path, no deadlock window)."""
    with open(data_path(SHORT_FIXTURE), "rb") as fh:
        body = fh.read()
    assert len(body) < BUFFER_SIZE
    await _serve_and_open(httpserver, body, SHORT_FIXTURE)


async def test_internet_source_long_stream_no_deadlock(httpserver: HTTPServer):
    """Regression test for #2849: streaming a file > BUFFER_SIZE must not deadlock."""
    with open(data_path(LONG_FIXTURE), "rb") as fh:
        body = fh.read()
    assert len(body) > BUFFER_SIZE
    await _serve_and_open(httpserver, body, LONG_FIXTURE)
