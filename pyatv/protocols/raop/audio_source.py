"""Audio sources that can provide raw PCM frames that pyatv can stream."""
from abc import ABC, abstractmethod
import asyncio
from contextlib import suppress
from functools import partial
import io
import logging
from typing import Optional, Union

import miniaudio
from miniaudio import SampleFormat

from pyatv.exceptions import NotSupportedError

_LOGGER = logging.getLogger(__name__)

FRAMES_PER_PACKET = 352


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

    async def close(self) -> None:
        """Close underlying resources."""

    @abstractmethod
    async def readframes(self, nframes: int) -> bytes:
        """Read number of frames and advance in stream."""

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


class ReaderWrapper(miniaudio.StreamableSource):
    """Wraps a reader into a StreamableSource that miniaudio can consume."""

    def __init__(self, reader: io.BufferedReader) -> None:
        """Initialize a new ReaderWrapper instance."""
        self.reader: io.BufferedReader = reader

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


class BufferedReaderSource(AudioSource):
    """Audio source used to play a file from a buffer.

    This audio source adds a small internal buffer (corresponding to 0,5s) to deal with
    tiny hiccups. Proper buffering should be done by the source buffer.
    """

    CHUNK_SIZE = FRAMES_PER_PACKET * 3

    def __init__(
        self,
        reader: miniaudio.WavFileReadStream,
        wrapper: ReaderWrapper,
        sample_rate: int,
        channels: int,
        sample_size: int,
    ) -> None:
        """Initialize a new MiniaudioWrapper instance."""
        self.loop = asyncio.get_event_loop()
        self.reader: miniaudio.WavFileReadStream = reader
        self.wrapper: ReaderWrapper = wrapper
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
        buffered_reader: io.BufferedReader,
        sample_rate: int,
        channels: int,
        sample_size: int,
    ) -> "BufferedReaderSource":
        """Return a new AudioSource instance playing from the provided buffer."""
        wrapper = ReaderWrapper(buffered_reader)
        loop = asyncio.get_event_loop()
        src = await loop.run_in_executor(
            None,
            partial(
                miniaudio.stream_any,
                wrapper,
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
        instance = cls(reader, wrapper, sample_rate, channels, sample_size)
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

        return data

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
            return b""

        bytes_to_read = (self.sample_size * self.channels) * nframes
        data = self.samples[self.pos : min(len(self.samples), self.pos + bytes_to_read)]
        self.pos += bytes_to_read
        return data

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
    source: Union[str, io.BufferedReader],
    sample_rate: int,
    channels: int,
    sample_size: int,
) -> AudioSource:
    """Create an AudioSource from given input source."""
    if isinstance(source, str):
        return await FileSource.open(source, sample_rate, channels, sample_size)
    return await BufferedReaderSource.open(source, sample_rate, channels, sample_size)
