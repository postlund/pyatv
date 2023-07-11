"""Dummy implementation of ALAC.

This is not by any means a proper implementation of ALAC, it merely serves as an
abstraction for creating ALAC frames compatible with the most common use case in
pyatv. It also simplifies decoding of frames in tests.

Some assumptions here:

* Endianness of samples are swapped from whatever is passed
* Samples are 16 bit/2 bytes
* Number of samples in a frame is derived from frame size
* End tag (111) is present at the end of a frame

NB: This module is currently not used as raw samples are sent instead of ALAC.
"""
from bitarray import bitarray


def encode(frames: bytes) -> bytes:
    """Encode audio samples into an ALAC frame."""
    # ALAC frame with raw data. Not so pretty but will work for now until a
    # proper ALAC encoder is added.
    # This assumes stereo mode. Basically reversed from here:
    # https://github.com/libav/libav/blob/c4642788e83b0858bca449f9b6e71ddb015dfa5d/libavcodec/alac.c#L407
    audio = bitarray()
    audio.extend("001" + (19 * "0") + "1")

    # Due to endianness, bytes must be sweapped here. Maybe format can be changed so
    # we don't have to?
    for i in range(0, len(frames), 2):
        audio.frombytes(bytes([frames[i + 1], frames[i]]))

    audio.extend("111")  # End tag (libav is picky about this)

    return audio.tobytes()


def decode(frame: bytes) -> bytes:
    """Decode audio sameples from an ALAC frame."""
    buffer = bitarray()
    buffer.frombytes(frame)

    # Audio starts 23 bits in and last bits must be removed because of the end tag
    buffer = buffer[23:-9]

    # Change byte order of samples to match encode
    for i in range(0, len(buffer), 16):
        lower_sample = buffer[i : i + 8]
        upper_sample = buffer[i + 8 : i + 16]
        buffer[i : i + 8] = upper_sample
        buffer[i + 8 : i + 16] = lower_sample

    return buffer.tobytes()
