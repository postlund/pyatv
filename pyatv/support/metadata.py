"""Convenience methods for extracting metadata from an audio file."""

import asyncio
import io
from typing import Union

from mediafile import MediaFile
from tinytag import TinyTag

from pyatv.interface import MediaMetadata

EMPTY_METADATA = MediaMetadata(None, None, None, None)


def _open_file(file: io.BufferedIOBase) -> MediaFile:
    start_position = file.tell()
    in_file = TinyTag.get(file_obj=file)
    file.seek(start_position)
    return in_file


async def get_metadata(file: Union[str, io.BufferedIOBase]) -> MediaMetadata:
    """Extract metadata from a file and return it."""
    loop = asyncio.get_event_loop()

    if isinstance(file, io.BufferedIOBase):
        tag = await loop.run_in_executor(None, _open_file, file)
    else:
        tag = await loop.run_in_executor(None, TinyTag.get, file)

    return MediaMetadata(
        title=tag.title,
        artist=tag.artist,
        album=tag.album,
        duration=tag.duration,
    )


def merge_into(base: MediaMetadata, new_metadata: MediaMetadata) -> MediaMetadata:
    """Merge missing fields into base metadata.

    Updates all fields with a None value in "new" with corresponding values from
    "new_metadata". Returns "base" again.
    """
    for field in base.__dataclass_fields__.keys():
        if getattr(base, field) is None:
            setattr(base, field, getattr(new_metadata, field))
    return base
