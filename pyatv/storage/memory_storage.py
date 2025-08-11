"""Memory storage module."""

from pyatv.storage import AbstractStorage

__pdoc_dev_page__ = "/development/storage"


class MemoryStorage(AbstractStorage):
    """Memory based storage module.

    This storage module stores settings in memory and everything stored with it will
    be forgotten when restarting the python interpreter.
    """

    async def save(self) -> None:
        """Save settings to active storage."""
        self.update_hash(dict(self))

    async def load(self) -> None:
        """Load settings from active storage."""

    def __str__(self) -> str:
        """Return string representation of MemoryStorage."""
        return "MemoryStorage"
