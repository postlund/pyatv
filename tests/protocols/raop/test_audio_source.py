"""Tests for pyatv.protocols.raop.audio_source (regression tests for #2849)."""

import asyncio
import os

import pytest

from pyatv.protocols.raop.audio_source import (
    BUFFER_SIZE,
    HEADROOM_SIZE,
    InternetSource,
    PatchedIceCastClient,
)
from pyatv.support.buffer import SemiSeekableBuffer

from tests.utils import data_path

pytestmark = pytest.mark.asyncio

SHORT_FIXTURE = "static_3sec.ogg"
LONG_FIXTURE = "audio_long.mp3"


async def _open_and_read(url: str) -> None:
    src = await InternetSource.open(url, sample_rate=44100, channels=2, sample_size=2)
    try:
        assert await src.readframes(352)
    finally:
        await src.close()


@pytest.mark.parametrize("files", [[SHORT_FIXTURE]])
async def test_internet_source_short_stream(data_webserver, files):
    assert os.path.getsize(data_path(files[0])) < BUFFER_SIZE
    await _open_and_read(data_webserver + files[0])


@pytest.mark.parametrize("files", [[LONG_FIXTURE]])
async def test_internet_source_long_stream_no_deadlock(data_webserver, files):
    assert os.path.getsize(data_path(files[0])) > BUFFER_SIZE
    await _open_and_read(data_webserver + files[0])


async def test_read_short_reads_when_producer_blocked(monkeypatch):
    body = bytes(4 * BUFFER_SIZE)

    class _FakeRaw:
        def __init__(self, data: bytes, chunk: int) -> None:
            self._data = data
            self._chunk = chunk
            self._pos = 0

        def read(self, num_bytes: int) -> bytes:
            num_bytes = min(num_bytes, self._chunk)
            data = self._data[self._pos : self._pos + num_bytes]
            self._pos += len(data)
            return data

    class _FakeHandle:
        status_code = 200
        reason = "OK"
        headers: dict = {}

        def __init__(self, raw: _FakeRaw) -> None:
            self.raw = raw

        def __enter__(self) -> "_FakeHandle":
            return self

        def __exit__(self, *exc) -> bool:
            return False

    monkeypatch.setattr(
        "pyatv.protocols.raop.audio_source.requests.get",
        lambda url, stream, timeout: _FakeHandle(_FakeRaw(body, 5000)),
    )

    buffer = SemiSeekableBuffer(
        BUFFER_SIZE, seekable_headroom=HEADROOM_SIZE, protected_headroom=False
    )
    loop = asyncio.get_event_loop()
    client = await loop.run_in_executor(None, PatchedIceCastClient, buffer, "http://x")
    try:
        data = await loop.run_in_executor(None, client.read, BUFFER_SIZE)
    finally:
        await loop.run_in_executor(None, client.close)

    assert data
    assert len(data) < BUFFER_SIZE
