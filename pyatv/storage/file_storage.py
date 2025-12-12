"""File based storage module."""

import asyncio
import json
import logging
from os import path
from pathlib import Path

from pyatv.storage import AbstractStorage, StorageModel

_LOGGER = logging.getLogger(__name__)

__pdoc_dev_page__ = "/development/storage"


class FileStorage(AbstractStorage):
    """Storage module storing settings in a file."""

    def __init__(self, filename: str, loop: asyncio.AbstractEventLoop) -> None:
        """Initialize a new FileStorage instance."""
        super().__init__()
        self._filename = filename
        self._loop = loop

    @staticmethod
    def default_storage(loop: asyncio.AbstractEventLoop) -> "FileStorage":
        r"""Return file storage with default path.

        This corresponds to the default file storage path that pyatv uses internally,
        e.g. in atvremote. Use this if you want to hook into that storage in your own
        applications.

        The path used for this file is $HOME/.pyatv.conf (C:\Users\<user>\.pyatv.conf
        on Windows).
        """
        return FileStorage(Path.home().joinpath(".pyatv.conf").as_posix(), loop)

    async def save(self) -> None:
        """Save settings to active storage."""
        dumped = dict(self)
        if self.has_changed(dumped):
            _LOGGER.debug("Saving settings to %s", self._filename)
            await self._loop.run_in_executor(None, self._save_file, dumped)
            self.update_hash(dumped)

    def _save_file(self, dumped: dict) -> None:
        with open(self._filename, "w", encoding="utf-8") as _fh:
            _fh.write(json.dumps(dumped) + "\n")

    async def load(self) -> None:
        """Load settings from active storage."""
        if path.exists(self._filename):
            _LOGGER.debug("Loading settings from %s", self._filename)
            model_json = await self._loop.run_in_executor(None, self._read_file)
            raw_data = json.loads(model_json)
            self.storage_model = StorageModel.parse_obj(raw_data)

            # Update hash based on what we read from file rather than serializing the
            # model. The reasonf for this is that pydantic might (because of
            # validators) modify the data we read and in that case we want to ensure
            # catch the update and actually save to file again when save is called.
            self.update_hash(raw_data)

    def _read_file(self) -> str:
        with open(self._filename, "r", encoding="utf-8") as _fh:
            return _fh.read()

    def __str__(self) -> str:
        """Return string representation of MemoryStorage."""
        return f"FileStorage:{self._filename}"
