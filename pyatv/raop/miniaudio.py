"""Basic wrapper for audio files that complies with Wave_read.

This module can read all file types supported by the miniaudio library and
provide an interface that is compatible with wave.Wave_read. Using this
wrapper, any file type supported by miniaudio can be played by the RAOP
implementation in pyatv.
"""
import asyncio
from functools import partial

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


class MiniaudioWrapper:
    """Wrapper for the miniaudio library.

    Only the parts needed by pyatv (in Wave_read) are implemented!
    """

    def __init__(
        self,
        src: miniaudio.DecodedSoundFile,
        sample_rate: int,
        channels: int,
        sample_size: int,
    ) -> None:
        """Initialize a new MiniaudioWrapper instance."""
        self.src: miniaudio.DecodedSoundFile = src
        self.samples: bytes = self.src.samples.tobytes()
        self.pos: int = 0

    @classmethod
    async def open(
        cls, filename: str, sample_rate: int, channels: int, sample_size: int
    ) -> "MiniaudioWrapper":
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
        return cls(src, sample_rate, channels, sample_size)

    def readframes(self, nframes: int) -> bytes:
        """Read number of frames and advance in stream."""
        if self.pos >= len(self.samples):
            return b""

        bytes_to_read = (self.getsampwidth() * self.getnchannels()) * nframes
        data = self.samples[self.pos : min(len(self.samples), self.pos + bytes_to_read)]
        self.pos += bytes_to_read
        return data

    def getframerate(self) -> int:
        """Return sample rate."""
        return self.src.sample_rate

    def getnchannels(self) -> int:
        """Return number of audio channels."""
        return self.src.nchannels

    def getsampwidth(self) -> int:
        """Return number of bytes per sample."""
        return self.src.sample_width

    def getduration(self) -> int:
        """Return duration in seconds."""
        return round(self.src.duration)
