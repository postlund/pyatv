"""Basic wrapper for audio files that complies with Wave_read.

This module can read all file types supported by the miniaudio library and
provide an interface that is compatible with wave.Wave_read. Using this
wrapper, any file type supported by miniaudio can be played by the RAOP
implementation in pyatv.
"""
from abc import ABC, abstractmethod, abstractproperty
import asyncio
from functools import partial
import io
from typing import Union

import miniaudio
from miniaudio import SampleFormat

from pyatv.exceptions import NotSupportedError


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

    @abstractmethod
    async def readframes(self, nframes: int) -> bytes:
        """Read number of frames and advance in stream."""

    @abstractproperty
    def sample_rate(self) -> int:
        """Return sample rate."""

    @abstractproperty
    def channels(self) -> int:
        """Return number of audio channels."""

    @abstractproperty
    def sample_size(self) -> int:
        """Return number of bytes per sample."""

    @abstractproperty
    def duration(self) -> int:
        """Return duration in seconds."""

    @abstractproperty
    def supports_seek(self) -> bool:
        """Return if source supports seeking."""


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
    """Wrapper for the miniaudio library.

    Only the parts needed by pyatv (in Wave_read) are implemented!
    """

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
        """Open an audio file and return an instance of MiniaudioWrapper."""
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
        return cls(reader, wrapper, sample_rate, channels, sample_size)

    async def readframes(self, nframes: int) -> bytes:
        """Read number of frames and advance in stream."""
        return await self.loop.run_in_executor(
            None, self.reader.read, nframes * self._sample_size * self._channels
        )

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

    @property
    def supports_seek(self) -> bool:
        """Return if source supports seeking."""
        return self.wrapper.reader.seekable()


class FileSource(AudioSource):
    """Wrapper for the miniaudio library.

    Only the parts needed by pyatv (in Wave_read) are implemented!
    """

    def __init__(self, src: miniaudio.DecodedSoundFile) -> None:
        """Initialize a new MiniaudioWrapper instance."""
        self.src: miniaudio.DecodedSoundFile = src
        self.samples: bytes = self.src.samples.tobytes()
        self.pos: int = 0

    @classmethod
    async def open(
        cls, filename: str, sample_rate: int, channels: int, sample_size: int
    ) -> "FileSource":
        """Open an audio file and return an instance of MiniaudioWrapper."""
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

    @property
    def supports_seek(self) -> bool:
        """Return if source supports seeking."""
        return True


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
