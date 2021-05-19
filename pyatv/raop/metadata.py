"""Convenience methods for extracting metadata from an audio file."""
from typing import NamedTuple, Optional

from audio_metadata import load


class AudioMetadata(NamedTuple):
    """Audio metadata."""

    title: Optional[str]
    artist: Optional[str]
    album: Optional[str]


EMPTY_METADATA = AudioMetadata(None, None, None)


def get_metadata(filename: str) -> AudioMetadata:
    """Extract metadata from a file and return it."""
    in_file = load(filename)

    # If no metadata, return something that can be easily compared with
    if not in_file.tags:
        return EMPTY_METADATA

    # All tags are always lists, so need to be joined into a string
    title = in_file.tags.get("title")
    artist = in_file.tags.get("artist")
    album = in_file.tags.get("album")

    return AudioMetadata(
        ", ".join(title) if title else None,
        ", ".join(artist) if artist else None,
        ", ".join(album) if album else None,
    )
