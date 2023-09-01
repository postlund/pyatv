"""File based storage module."""
import asyncio
import json
import logging
from os import path

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

    async def save(self) -> None:
        """Save settings to active storage."""
        if self.changed:
            _LOGGER.debug("Saving settings to %s", self._filename)
            await self._loop.run_in_executor(None, self._save_file)
            self.mark_as_saved()

    def _save_file(self) -> None:
        # If settings are empty for a device (e.e. no settings overridden or credentials
        # saved), then the output will just be an empty dict. To not pollute the output
        # with those, we do some filtering here.
        dumped = self.storage_model.model_dump(exclude_defaults=True)
        dumped["devices"] = [device for device in dumped["devices"] if device != {}]

        with open(self._filename, "w", encoding="utf-8") as _fh:
            _fh.write(json.dumps(dumped) + "\n")

    async def load(self) -> None:
        """Load settings from active storage."""
        if path.exists(self._filename):
            _LOGGER.debug("Loading settings from %s", self._filename)
            model_json = await self._loop.run_in_executor(None, self._read_file)
            self.storage_model = StorageModel(**json.loads(model_json))
            self.mark_as_saved()

    def _read_file(self) -> str:
        with open(self._filename, "r", encoding="utf-8") as _fh:
            return _fh.read()

    def __str__(self) -> str:
        """Return string representation of MemoryStorage."""
        return f"FileStorage:{self._filename}"
