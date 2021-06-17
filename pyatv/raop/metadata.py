"""Convenience methods for extracting metadata from an audio file."""
import asyncio
import io
from typing import NamedTuple, Optional, Union

from audio_metadata import load


class AudioMetadata(NamedTuple):
    """Audio metadata."""

    title: Optional[str]
    artist: Optional[str]
    album: Optional[str]
    duration: Optional[float]


EMPTY_METADATA = AudioMetadata(None, None, None, None)


async def get_metadata(file: Union[str, io.BufferedReader]) -> AudioMetadata:
    """Extract metadata from a file and return it."""
    loop = asyncio.get_event_loop()
    in_file = await loop.run_in_executor(None, load, file)

    # If no metadata, return something that can be easily compared with
    if not in_file.tags:
        return EMPTY_METADATA

    duration = in_file.streaminfo.get("duration")

    # All tags are always lists, so need to be joined into a string
    title = in_file.tags.get("title")
    artist = in_file.tags.get("artist")
    album = in_file.tags.get("album")

    return AudioMetadata(
        ", ".join(title) if title else None,
        ", ".join(artist) if artist else None,
        ", ".join(album) if album else None,
        duration,
    )
