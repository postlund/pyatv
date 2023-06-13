"""Convenience methods for extracting metadata from an audio file."""
import asyncio
import io
from typing import Union

from mediafile import MediaFile

from pyatv.interface import MediaMetadata

EMPTY_METADATA = MediaMetadata(None, None, None, None)


def _open_file(file: io.BufferedIOBase) -> MediaFile:
    start_position = file.tell()
    in_file = MediaFile(file)
    file.seek(start_position)
    return in_file


async def get_metadata(file: Union[str, io.BufferedIOBase]) -> MediaMetadata:
    """Extract metadata from a file and return it."""
    loop = asyncio.get_event_loop()

    if isinstance(file, io.BufferedIOBase):
        in_file = await loop.run_in_executor(None, _open_file, file)
    else:
        in_file = await loop.run_in_executor(None, MediaFile, file)

    return MediaMetadata(
        in_file.title,
        in_file.artist,
        in_file.album,
        in_file.length,
    )
