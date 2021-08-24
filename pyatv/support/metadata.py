"""Convenience methods for extracting metadata from an audio file."""
import asyncio
import io
from typing import NamedTuple, Optional, Union

from mediafile import MediaFile


class AudioMetadata(NamedTuple):
    """Audio metadata."""

    title: Optional[str]
    artist: Optional[str]
    album: Optional[str]
    duration: Optional[float]


EMPTY_METADATA = AudioMetadata(None, None, None, None)


def _open_file(file: io.BufferedReader) -> MediaFile:
    start_position = file.tell()
    in_file = MediaFile(file)
    file.seek(start_position)
    return in_file


async def get_metadata(file: Union[str, io.BufferedReader]) -> AudioMetadata:
    """Extract metadata from a file and return it."""
    loop = asyncio.get_event_loop()

    if isinstance(file, io.BufferedReader):
        in_file = await loop.run_in_executor(None, _open_file, file)
    else:
        in_file = await loop.run_in_executor(None, MediaFile, file)

    return AudioMetadata(
        in_file.title,
        in_file.artist,
        in_file.album,
        in_file.length,
    )
