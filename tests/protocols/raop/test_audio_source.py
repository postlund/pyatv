"""Tests for pyatv.protocols.raop.audio_source.

Includes a regression test for #2849: streaming a media file larger than
PatchedIceCastClient's internal BUFFER_SIZE must not deadlock during
miniaudio's decoder init.
"""

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

SHORT_FIXTURE = "static_3sec.ogg"  # existing, ~4 KiB
LONG_FIXTURE = "audio_long.mp3"  # new, just over BUFFER_SIZE


async def _open_and_read(url: str) -> None:
    src = await InternetSource.open(url, sample_rate=44100, channels=2, sample_size=2)
    try:
        frames = await src.readframes(352)
        assert frames, "InternetSource returned no audio frames after init"
    finally:
        await src.close()


@pytest.mark.parametrize("files", [[SHORT_FIXTURE]])
async def test_internet_source_short_stream(data_webserver, files):
    """Streaming a small file over HTTP works (fast path, no deadlock window)."""
    assert os.path.getsize(data_path(files[0])) < BUFFER_SIZE
    await _open_and_read(data_webserver + files[0])


@pytest.mark.parametrize("files", [[LONG_FIXTURE]])
async def test_internet_source_long_stream_no_deadlock(data_webserver, files):
    """Regression test for #2849: streaming a file > BUFFER_SIZE must not deadlock."""
    assert os.path.getsize(data_path(files[0])) > BUFFER_SIZE
    await _open_and_read(data_webserver + files[0])


async def test_read_short_reads_when_producer_blocked(monkeypatch):
    """Regression test for the #2849 deadlock on non-BUFFER_SIZE-aligned streams.

    The HTTP tests above use Content-Length responses, so the downloader reads
    full BLOCK_SIZE chunks and the raw buffer happens to land on exactly
    BUFFER_SIZE -- the one value an old ``fits(1)`` break caught. Real streams
    (icy-metaint, chunked transfer-encoding, slow sockets) return short reads,
    settling the raw buffer inside (BUFFER_SIZE - BLOCK_SIZE, BUFFER_SIZE) where
    the producer is blocked. The reader must short-read there rather than wait
    for data that can never arrive. This drives PatchedIceCastClient directly
    (no miniaudio) with a transport that always returns short reads.
    """
    body = bytes(4 * BUFFER_SIZE)

    class _FakeRaw:
        def __init__(self, data: bytes, chunk: int) -> None:
            self._data = data
            self._chunk = chunk
            self._pos = 0

        def read(self, num_bytes: int) -> bytes:
            # Always return fewer than BLOCK_SIZE so the raw buffer settles inside
            # the gap rather than on the BUFFER_SIZE boundary.
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
        # Mimic miniaudio's decoder-init read of a full BUFFER_SIZE. Before the
        # fix this blocks until DEFAULT_TIMEOUT (OperationTimeoutError); now it
        # returns a short read as soon as the producer is blocked.
        data = await loop.run_in_executor(None, client.read, BUFFER_SIZE)
    finally:
        await loop.run_in_executor(None, client.close)

    assert data, "read deadlocked instead of returning a short read"
    assert len(data) < BUFFER_SIZE
