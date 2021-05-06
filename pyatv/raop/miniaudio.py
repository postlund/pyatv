"""Basic wrapper for audio files that complies with Wave_read.

This module can read all file types supported by the miniaudio library and
provide an interface that is compatible with wave.Wave_read. Using this
wrapper, any file type supported by miniaudio can be played by the RAOP
implementation in pyatv.
"""
import miniaudio


class MiniaudioWrapper:
    """Wrapper for the miniaudio library.

    Only the parts needed by pyatv (in Wave_read) are implemented!
    """

    def __init__(self, filename) -> None:
        """Initialize a new MiniaudioWrapper instance."""
        self.src = miniaudio.decode_file(filename)
        self.samples = self.src.samples.tobytes()
        self.pos = 0

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
