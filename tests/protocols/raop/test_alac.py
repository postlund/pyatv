"""Unit tests for pyatv.protocols.raop.alac."""
from pyatv.protocols.raop import alac

AUDIO_FRAMES = b"\x01\x02\x03\x04"


def test_encode_and_decode():
    encoded = alac.encode(AUDIO_FRAMES)
    decoded = alac.decode(encoded)
    assert decoded == AUDIO_FRAMES
