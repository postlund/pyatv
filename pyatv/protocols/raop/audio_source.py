"""Audio sources that can provide raw PCM frames that pyatv can stream."""

from abc import ABC, abstractmethod
import array
import asyncio
from contextlib import suppress
from functools import partial
import io
import logging
import math
import re
import sys
import threading
import time
from typing import Generator, Optional, Union

import miniaudio
from miniaudio import SampleFormat
import requests

from pyatv.exceptions import NotSupportedError, OperationTimeoutError, ProtocolError
from pyatv.interface import MediaMetadata
from pyatv.support.buffer import SemiSeekableBuffer
from pyatv.support.metadata import EMPTY_METADATA, get_metadata

_LOGGER = logging.getLogger(__name__)

FRAMES_PER_PACKET = 352

DEFAULT_TIMEOUT = 10.0  # Seconds

BUFFER_SIZE = 64 * 1024
HEADROOM_SIZE = 32 * 1024


def _to_audio_samples(data: Union[bytes, array.array]) -> bytes:
    output: array.array
    if isinstance(data, bytes):
        # TODO: This assumes s16 samples!
        output = array.array("h", data)
    else:
        output = data

    # TODO: According to my investigation in #2057, this should happen if system
    # byteorder is "big". So not sure why this works...
    if sys.byteorder == "little":
        output.byteswap()

    return output.tobytes()


def _int2sf(sample_size: int) -> SampleFormat:
    if sample_size == 1:
        return SampleFormat.UNSIGNED8
    if sample_size == 2:
        return SampleFormat.SIGNED16
    if sample_size == 3:
        return SampleFormat.SIGNED24
    if sample_size == 4:
        return SampleFormat.SIGNED32
    raise NotSupportedError(f"unsupported sample size: {sample_size}")


class AudioSource(ABC):
    """Audio source that returns raw PCM frames."""

    NO_FRAMES = b""

    async def close(self) -> None:
        """Close underlying resources."""

    @abstractmethod
    async def readframes(self, nframes: int) -> bytes:
        """Read number of frames and advance in stream.

        Frames are returned in little endian to match what AirPlay expects.
        """

    @abstractmethod
    async def get_metadata(self) -> MediaMetadata:
        """Return media metadata if available and possible."""

    @property
    @abstractmethod
    def sample_rate(self) -> int:
        """Return sample rate."""

    @property
    @abstractmethod
    def channels(self) -> int:
        """Return number of audio channels."""

    @property
    @abstractmethod
    def sample_size(self) -> int:
        """Return number of bytes per sample."""

    @property
    @abstractmethod
    def duration(self) -> int:
        """Return duration in seconds."""


class StreamableIOBaseWrapper(miniaudio.StreamableSource):
    """Wraps a reader into a StreamableSource that miniaudio can consume."""

    def __init__(self, reader: io.BufferedIOBase) -> None:
        """Initialize a new ReaderWrapper instance."""
        self.reader: io.BufferedIOBase = reader

    def read(self, num_bytes: int) -> Union[bytes, memoryview]:
        """Read and return data from buffer."""
        return self.reader.read(num_bytes)

    def seek(self, offset: int, origin: miniaudio.SeekOrigin) -> bool:
        """Seek in stream."""
        if not self.reader.seekable():
            return False

        whence = 1 if origin == miniaudio.SeekOrigin.CURRENT else 0
        self.reader.seek(offset, whence)
        return True


class BufferedIOBaseWrapper(io.BufferedIOBase):
    """Wrap a BufferedIOBase, making it seekable."""

    def __init__(self, reader: io.BufferedIOBase, buffer: SemiSeekableBuffer) -> None:
        """Initialize a new BufferedIOBaseWrapper instance."""
        self.reader: io.BufferedIOBase = reader
        self.buffer: SemiSeekableBuffer = buffer
        self.name = "stream"

    def read(self, size=-1):
        """Read bytes from stream."""
        if size == 0:
            return b""

        # If space left in buffer, read from source and add it there. Don't do it if
        # there's enough data in the buffer already though.
        left_in_buffer = self.buffer.remaining
        if left_in_buffer > 0 and size != -1 and size > self.buffer.size:
            self.buffer.add(self.reader.read(min(size, left_in_buffer)))

        to_read = self.buffer.size if size == -1 else min(size, self.buffer.size)
        return self.buffer.get(to_read)

    def seek(self, pos, origin=io.SEEK_SET):
        """Seek to position in stream."""
        if origin == io.SEEK_SET:
            self.buffer.seek(pos)
        return self.buffer.position

    def tell(self):
        """Return current position in stream."""
        return self.buffer.position

    def seekable(self):
        """Return a bool indicating whether object supports random access."""
        return True

    def readable(self):
        """Return a bool indicating whether object was opened for reading."""
        return True


class StreamReaderWrapper(miniaudio.StreamableSource):
    """Wraps a reader into a StreamableSource that miniaudio can consume."""

    def __init__(
        self, reader: asyncio.streams.StreamReader, buffer: SemiSeekableBuffer
    ) -> None:
        """Initialize a new ReaderWrapper instance."""
        self.reader: asyncio.streams.StreamReader = reader
        self.buffer: SemiSeekableBuffer = buffer
        self.loop = asyncio.get_event_loop()

    def read(self, num_bytes: int = -1) -> Union[bytes, memoryview]:
        """Read and return data from buffer."""
        if num_bytes == 0:
            return b""

        # Read all data (if -1), otherwise as much as request OR space left in buffer
        if self.buffer.position > 0 and self.buffer.size == 0:
            return asyncio.run_coroutine_threadsafe(
                self.reader.read(num_bytes), self.loop
            ).result()

        to_read = self.buffer.size if num_bytes == -1 else num_bytes
        to_read = min(to_read, BUFFER_SIZE - self.buffer.size)

        self.buffer.add(
            asyncio.run_coroutine_threadsafe(
                self.reader.read(to_read), self.loop
            ).result()
        )

        return self.buffer.get(to_read)

    def seek(
        self, offset: int, origin: miniaudio.SeekOrigin = miniaudio.SeekOrigin.START
    ) -> bool:
        """Seek to position in stream."""
        if origin in (miniaudio.SeekOrigin.START, 0):
            return self.buffer.seek(offset)
        return False

    def tell(self):
        """Return current position in stream."""
        return self.buffer.position


class StreamableSourceWrapper(io.BufferedIOBase):
    """Wraps a StreambleSource, making it seekable."""

    def __init__(
        self,
        source: miniaudio.StreamableSource,
        buffer: SemiSeekableBuffer,
        /,
        name: str = "stream"
    ) -> None:
        """Initialize a new StreamableSourceWrapper instance."""
        super().__init__()
        self.source = source
        self.buffer = buffer
        # Medafile uses this in error messages, so it helps for debugging
        self.name = name

    def read(self, size=-1):
        """Read bytes from stream."""
        return self.source.read(size)

    def seek(self, pos, origin=io.SEEK_SET):
        """Seek to position in stream."""
        if origin == io.SEEK_SET:
            self.source.seek(pos, miniaudio.SeekOrigin.START)
        return self.buffer.position

    def tell(self):
        """Return current position in stream."""
        return self.buffer.position

    def seekable(self):
        """Return a bool indicating whether object supports random access."""
        return True

    def readable(self):
        """Return a bool indicating whether object was opened for reading."""
        return True


async def get_buffered_io_metadata(buffer: io.BufferedIOBase) -> MediaMetadata:
    """Read metadata from a BufferedIOBase.

    This method will restore position to previous position after reading.
    """
    # Save position in buffer before parsing metadata so we can restore it afterwards
    before = buffer.tell()
    if buffer.seek(0) != 0:
        return EMPTY_METADATA

    try:
        return await get_metadata(buffer)
    except Exception:
        logging.exception("Failed to parse metadata")
    finally:
        buffer.seek(0)
        if buffer.seek(before) != before:
            logging.warning("Failed to restore position to %d", before)

    return EMPTY_METADATA


class BufferedIOBaseSource(AudioSource):
    """Audio source used to play a file from a buffer.

    This audio source adds a small internal buffer (corresponding to 0,5s) to deal with
    tiny hiccups. Proper buffering should be done by the source buffer.
    """

    CHUNK_SIZE = FRAMES_PER_PACKET * 3

    def __init__(
        self,
        reader: miniaudio.WavFileReadStream,
        source: miniaudio.StreamableSource,
        metadata: MediaMetadata,
        sample_rate: int,
        channels: int,
        sample_size: int,
    ) -> None:
        """Initialize a new MiniaudioWrapper instance."""
        self.loop = asyncio.get_event_loop()
        self.reader: miniaudio.WavFileReadStream = reader
        self.source: miniaudio.StreamableSource = source
        self.metadata = metadata
        self._buffer_task: Optional[asyncio.Task] = asyncio.ensure_future(
            self._buffering_task()
        )
        self._audio_buffer: bytes = b""
        self._buffer_needs_refilling: asyncio.Event = asyncio.Event()
        self._data_was_added_to_buffer: asyncio.Event = asyncio.Event()
        self._buffer_size: int = int(sample_rate / 2)
        self._sample_rate: int = sample_rate
        self._channels: int = channels
        self._sample_size: int = sample_size

    @classmethod
    async def open(
        cls,
        source: Union[io.BufferedIOBase, asyncio.streams.StreamReader],
        sample_rate: int,
        channels: int,
        sample_size: int,
    ) -> "BufferedIOBaseSource":
        """Return a new AudioSource instance playing from the provided buffer."""
        loop = asyncio.get_event_loop()

        buffer = SemiSeekableBuffer(
            BUFFER_SIZE, seekable_headroom=HEADROOM_SIZE, protected_headroom=True
        )

        # Use correct wrapper when streaming from buffer to ensure we have some kind
        # of seek support
        if isinstance(source, io.BufferedIOBase):
            if source.seekable():
                metadata_source = source
            else:
                metadata_source = BufferedIOBaseWrapper(source, buffer)
            streamable_source = StreamableIOBaseWrapper(metadata_source)
        else:
            streamable_source = StreamReaderWrapper(source, buffer)
            metadata_source = StreamableSourceWrapper(streamable_source, buffer)

        metadata = await get_buffered_io_metadata(metadata_source)
        buffer.protected_headroom = False

        src = await loop.run_in_executor(
            None,
            partial(
                miniaudio.stream_any,
                streamable_source,
                output_format=_int2sf(sample_size),
                nchannels=channels,
                sample_rate=sample_rate,
            ),
        )

        reader = miniaudio.WavFileReadStream(
            src, sample_rate, channels, _int2sf(sample_size)
        )

        # TODO: We get a WAV file back, but we expect to return raw PCM samples so
        # the WAVE header must be removed. It would be better to actually parse the
        # header, ensuring we remove the correct amount of data. But for now we are
        # lazy.
        await loop.run_in_executor(None, reader.read, 44)

        # The source stream is passed here and saved to not be garbage collected
        instance = cls(
            reader, streamable_source, metadata, sample_rate, channels, sample_size
        )
        return instance

    async def close(self) -> None:
        """Close underlying resources."""
        if self._buffer_task:
            self._buffer_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._buffer_task
            self._buffer_task = None

    async def readframes(self, nframes: int) -> bytes:
        """Read number of frames and advance in stream."""
        # If buffer is empty but the buffering task is still running, that means we are
        # buffering and need to wait for more data to be added to buffer.
        buffer_task_running = self._buffer_task and self._buffer_task.done()
        if not self._audio_buffer and not buffer_task_running:
            _LOGGER.debug("Audio source is buffering")
            self._buffer_needs_refilling.set()
            self._data_was_added_to_buffer.clear()
            await self._data_was_added_to_buffer.wait()

        total_bytes = nframes * self._sample_size * self._channels

        # Return data corresponding to requested frame, or what is left
        available_data = min(total_bytes, len(self._audio_buffer))
        data = self._audio_buffer[0:available_data]
        self._audio_buffer = self._audio_buffer[available_data:]

        # Simple buffering scheme: fill up the buffer again when reaching <= 50%
        if len(self._audio_buffer) < 0.5 * self._buffer_size:
            self._buffer_needs_refilling.set()

        return _to_audio_samples(data)

    async def get_metadata(self) -> MediaMetadata:
        """Return media metadata if available and possible."""
        return self.metadata

    async def _buffering_task(self) -> None:
        _LOGGER.debug("Starting audio buffering task")
        while True:
            try:
                # Read a chunk and add it to the internal buffer. If no data as read,
                # just break out.
                chunk = await self.loop.run_in_executor(
                    None, self.reader.read, self.CHUNK_SIZE
                )
                if not chunk:
                    break

                self._audio_buffer += chunk

                # Wait for an entire packet
                if (
                    len(self._audio_buffer)
                    >= FRAMES_PER_PACKET * self._channels * self._sample_size
                ):
                    self._data_was_added_to_buffer.set()

                if len(self._audio_buffer) >= self._buffer_size:
                    await self._buffer_needs_refilling.wait()
                    self._buffer_needs_refilling.clear()

            except Exception:
                _LOGGER.exception("an error occurred during buffering")

        self._data_was_added_to_buffer.set()

    @property
    def sample_rate(self) -> int:
        """Return sample rate."""
        return self._sample_rate

    @property
    def channels(self) -> int:
        """Return number of audio channels."""
        return self._channels

    @property
    def sample_size(self) -> int:
        """Return number of bytes per sample."""
        return self._sample_size

    @property
    def duration(self) -> int:
        """Return duration in seconds."""
        return 0  # We don't know the duration


# This is a "patched" version of the IceCastClient from pyminiaudio, but everything
# not used by pyatv has been ripped out and urllib is replaced by requests. Apparently
# Cloudflare is blocking requests by urllib, so better to use requests instead which
# is better anyway. See #1546 for details.
# NB: This is not a perfect implementation in any way, improvements are welcome!
class PatchedIceCastClient(miniaudio.StreamableSource):
    """Patched version of IceCastClient that breaks when all data has been read."""

    BLOCK_SIZE = 8 * 1024

    def __init__(self, buffer: SemiSeekableBuffer, url: str) -> None:
        """Initialize a new PatchedIceCastClient instance."""
        self.url = url
        self.error_message: Optional[str] = None
        self._stop_stream: bool = False
        self._buffer: SemiSeekableBuffer = buffer
        self._buffer_lock = threading.Lock()
        self._download_thread = threading.Thread(
            target=self._stream_wrapper, daemon=True
        )
        self._download_thread.start()

    def seek(self, offset: int, origin: miniaudio.SeekOrigin) -> bool:
        """Seek in current audio stream."""
        # SemiSeekableBuffer only supports seeking from start
        if origin == miniaudio.SeekOrigin.START:
            return self._buffer.seek(offset)
        return False

    def read(self, num_bytes: int) -> bytes:
        """Read a chunk of data from the stream."""
        start_time = time.monotonic()

        # TODO: Should not be based on polling
        while len(self._buffer) < num_bytes and not self._stop_stream:
            if time.monotonic() - start_time > DEFAULT_TIMEOUT:
                raise OperationTimeoutError("timed out reading from stream")

            time.sleep(0.1)

        with self._buffer_lock:
            data = self._buffer.get(num_bytes)
            return data

    def close(self) -> None:
        """Stop the stream, aborting the background downloading."""
        self._stop_stream = True
        self._download_thread.join()

    def _readall(self, fileobject, size: int) -> bytes:
        buffer = b""
        while len(buffer) < size:
            buffer += fileobject.read(size)
        return buffer

    def _stream_wrapper(self) -> None:
        try:
            self._download_stream()
        except Exception as ex:
            self.error_message = str(ex)
            _LOGGER.debug("Error during streaming: %s", self.error_message)
        self._stop_stream = True

    def _download_stream(self) -> None:  # pylint: disable=too-many-branches
        with requests.get(self.url, stream=True, timeout=10.0) as handle:
            if handle.status_code < 200 or handle.status_code >= 300:
                raise ProtocolError(
                    f"Got status {handle.status_code} with message: {handle.reason}"
                )
            result = handle.raw
            if "icy-metaint" in handle.headers:
                meta_interval = int(result.headers["icy-metaint"])
            else:
                meta_interval = 0

            while not self._stop_stream:
                # Wait for space in buffer
                # TODO: Should be lock-based instead of polling
                while not self._buffer.fits(self.BLOCK_SIZE):
                    time.sleep(0.1)
                    if self._stop_stream:
                        return

                # Read data from response
                if meta_interval:
                    chunk = self._readall(result, meta_interval)
                    meta_size = 16 * self._readall(result, 1)[0]
                    self._readall(result, meta_size)
                else:
                    chunk = result.read(self.BLOCK_SIZE)
                    if chunk == b"":
                        _LOGGER.debug("HTTP streaming ended")
                        self._stop_stream = True

                # Add produced chunk to internal buffer
                with self._buffer_lock:
                    self._buffer.add(chunk)


class InternetSource(AudioSource):
    """Audio source used to stream from an Internet source (HTTP)."""

    def __init__(
        self,
        source: miniaudio.StreamableSource,
        stream_generator: Generator[array.array, int, None],
        metadata: MediaMetadata,
        sample_rate: int,
        channels: int,
        sample_size: int,
    ):
        """Initialize a new InternetSource instance."""
        self.source = source
        self.stream_generator = stream_generator
        self.metadata = metadata
        self.loop = asyncio.get_event_loop()
        self._sample_rate = sample_rate
        self._channels = channels
        self._sample_size = sample_size

    @classmethod
    async def open(
        cls,
        url: str,
        sample_rate: int,
        channels: int,
        sample_size: int,
    ) -> "InternetSource":
        """Return a new AudioSource instance playing from the provided URL."""
        buffer = SemiSeekableBuffer(
            BUFFER_SIZE,
            seekable_headroom=HEADROOM_SIZE,
            protected_headroom=True,
        )
        loop = asyncio.get_event_loop()
        source = await loop.run_in_executor(None, PatchedIceCastClient, buffer, url)

        # Read metadata prior to starting to stream to ensure we are at the
        # beginning. Position will be restored to 0 afterwards.
        metadata = await get_buffered_io_metadata(
            StreamableSourceWrapper(source, buffer, name=url)
        )
        buffer.protected_headroom = False

        try:
            stream_generator = await loop.run_in_executor(
                None,
                partial(
                    miniaudio.stream_any,
                    source,
                    frames_to_read=FRAMES_PER_PACKET,
                    output_format=_int2sf(sample_size),
                    nchannels=channels,
                    sample_rate=sample_rate,
                ),
            )
        except miniaudio.DecodeError as ex:
            if source.error_message is not None:
                raise ProtocolError(source.error_message) from ex
            raise

        return cls(
            source, stream_generator, metadata, sample_rate, channels, sample_size
        )

    async def close(self) -> None:
        """Close underlying resources."""
        await self.loop.run_in_executor(None, self.source.close)

    async def readframes(self, nframes: int) -> bytes:
        """Read number of frames and advance in stream."""
        with suppress(StopIteration):
            frames: Optional[array.array] = next(self.stream_generator)
            if frames:
                return _to_audio_samples(frames)
        return AudioSource.NO_FRAMES

    async def get_metadata(self) -> MediaMetadata:
        """Return media metadata if available and possible."""
        return self.metadata

    @property
    def sample_rate(self) -> int:
        """Return sample rate."""
        return self._sample_rate

    @property
    def channels(self) -> int:
        """Return number of audio channels."""
        return self._channels

    @property
    def sample_size(self) -> int:
        """Return number of bytes per sample."""
        return self._sample_size

    @property
    def duration(self) -> int:
        """Return duration in seconds."""
        return math.ceil(self.metadata.duration or 0)


class FileSource(AudioSource):
    """Audio source used to play a local audio file."""

    def __init__(self, src: miniaudio.DecodedSoundFile) -> None:
        """Initialize a new FileSource instance."""
        self.src: miniaudio.DecodedSoundFile = src
        self.samples: bytes = self.src.samples.tobytes()
        self.pos: int = 0

    @classmethod
    async def open(
        cls, filename: str, sample_rate: int, channels: int, sample_size: int
    ) -> "FileSource":
        """Return a new AudioSource instance playing from the provided file."""
        loop = asyncio.get_event_loop()
        src = await loop.run_in_executor(
            None,
            partial(
                miniaudio.decode_file,
                filename,
                output_format=_int2sf(sample_size),
                nchannels=channels,
                sample_rate=sample_rate,
            ),
        )
        return cls(src)

    async def readframes(self, nframes: int) -> bytes:
        """Read number of frames and advance in stream."""
        if self.pos >= len(self.samples):
            return AudioSource.NO_FRAMES

        bytes_to_read = (self.sample_size * self.channels) * nframes
        data = self.samples[self.pos : min(len(self.samples), self.pos + bytes_to_read)]
        self.pos += bytes_to_read
        return _to_audio_samples(data)

    async def get_metadata(self) -> MediaMetadata:
        """Return media metadata if available and possible."""
        try:
            return await get_metadata(self.src.name)
        except Exception as ex:
            _LOGGER.warning("Failed to load metadata from %s: %s", self.src.name, ex)
        return EMPTY_METADATA

    @property
    def sample_rate(self) -> int:
        """Return sample rate."""
        return self.src.sample_rate

    @property
    def channels(self) -> int:
        """Return number of audio channels."""
        return self.src.nchannels

    @property
    def sample_size(self) -> int:
        """Return number of bytes per sample."""
        return self.src.sample_width

    @property
    def duration(self) -> int:
        """Return duration in seconds."""
        return round(self.src.duration)


async def open_source(
    source: Union[str, io.BufferedIOBase, asyncio.streams.StreamReader],
    sample_rate: int,
    channels: int,
    sample_size: int,
) -> AudioSource:
    """Create an AudioSource from given input source."""
    if isinstance(source, str):
        if re.match("^http(|s)://", source):
            return await InternetSource.open(source, sample_rate, channels, sample_size)
        return await FileSource.open(source, sample_rate, channels, sample_size)

    return await BufferedIOBaseSource.open(source, sample_rate, channels, sample_size)
