"""Storage module."""

from hashlib import sha256
import json
from typing import Any, Iterator, List, Sequence, Tuple

from pyatv.const import Protocol
from pyatv.exceptions import DeviceIdMissingError, SettingsError
from pyatv.interface import BaseConfig, Storage
from pyatv.settings import Settings
from pyatv.support.pydantic_compat import BaseModel, model_copy

__pdoc_dev_page__ = "/development/storage"

__pdoc__ = {
    "StorageModel.model_config": False,
    "StorageModel.model_fields": False,
}

MODEL_VERSION = 1


def _dict_hash(data: dict) -> str:
    # Calculate a hash of all settings by dumping content to JSON and hashing all
    # output using SHA256 (arbitrarily chosen for now). This is not very efficient
    # (especially when making multiple calls) but should be reliable and good enough.
    hasher = sha256()
    hasher.update(json.dumps(data).encode("utf-8"))
    return hasher.hexdigest()


# This is the model we save "somewhere" (to file, cloud, etc). It is mainly a copy of
# all device settings, but may also contain some additional metadata.
class StorageModel(BaseModel, extra="ignore"):  # type: ignore[call-arg]
    """Storage model of data that is saved or restored to underlying storage."""

    version: int
    devices: List[Settings]


class AbstractStorage(Storage):
    """Abstract base class handling all logic except for saving and loading.

    New storage modules should generally inherit from this class and implement save and
    load according to the underlying storage mechanism.
    """

    def __init__(self) -> None:
        """Initialize a new AbstractStorage instance."""
        self._settings: List[Settings] = []
        self._hash: str = _dict_hash({})

    def has_changed(self, data: dict) -> bool:
        """Return if anything has changed in the model since loading.

        This method compares a hash of the saved data with the provided data to deduce
        if anything has changed.
        """
        return self._hash != _dict_hash(data)

    @property
    def settings(self) -> Sequence[Settings]:
        """Return settings for all devices."""
        return self._settings

    @property
    def storage_model(self) -> StorageModel:
        """Return storage model representation."""
        return StorageModel(version=MODEL_VERSION, devices=self._settings)

    @storage_model.setter
    def storage_model(self, other: StorageModel) -> None:
        """Set storage model data."""
        if other.version != MODEL_VERSION:
            raise SettingsError(f"unsupported version: {other.version}")
        self._settings = other.devices

    def update_hash(self, data: dict) -> None:
        """Call after saving to indicate settings have been saved."""
        self._hash = _dict_hash(data)

    async def get_settings(self, config: BaseConfig) -> Settings:
        """Return settings for a specific configuration (device).

        The returned Settings object is a reference to an object in the storage module.
        Changes made can/will be written back to the storage in case "save" is called.

        If no settings exists for the current configuration, new settings are created
        automatically and returned. If the configuration does not contain any valid
        identitiers, DeviceIdMissingError will be raised.

        If settings exists for a configuration but mismatch, they will be automatically
        updated in the storage. Set ignore_update to False to not update storage.
        """
        identifiers = config.all_identifiers
        if not identifiers:
            raise DeviceIdMissingError(f"no identifier for device {config.name}")

        # Find existing settings if we have it
        for settings in self._settings:
            # TODO: Clean this up/make more general
            if (
                (settings.protocols.airplay.identifier in identifiers)
                or (settings.protocols.companion.identifier in identifiers)
                or (settings.protocols.dmap.identifier in identifiers)
                or (settings.protocols.mrp.identifier in identifiers)
                or (settings.protocols.raop.identifier in identifiers)
            ):
                return settings

        # If no settings were found, create new ones
        settings = Settings()
        self._update_settings_from_config(config, settings)
        self._settings.append(settings)
        return settings

    async def remove_settings(self, settings: Settings) -> bool:
        """Remove settings from storage.

        Returns True if settings were removed, otherwise False.
        """
        if settings in self._settings:
            self._settings.remove(settings)
            return True
        return False

    async def update_settings(self, config: BaseConfig) -> None:
        """Update settings based on config.

        This method extracts settings from a configuration and writes them back to
        the storage.
        """
        settings = await self.get_settings(config)
        self._update_settings_from_config(config, settings)

    @staticmethod
    def _update_settings_from_config(config: BaseConfig, settings: Settings) -> None:
        for service in config.services:
            # TODO: Clean this up/make more general
            if service.protocol == Protocol.AirPlay:
                settings.protocols.airplay = model_copy(
                    settings.protocols.airplay, update=service.settings()
                )
                settings.protocols.airplay.identifier = service.identifier
            elif service.protocol == Protocol.DMAP:
                settings.protocols.dmap = model_copy(
                    settings.protocols.dmap, update=service.settings()
                )
                settings.protocols.dmap.identifier = service.identifier
            elif service.protocol == Protocol.Companion:
                settings.protocols.companion = model_copy(
                    settings.protocols.companion, update=service.settings()
                )
                settings.protocols.companion.identifier = service.identifier
            elif service.protocol == Protocol.MRP:
                settings.protocols.mrp = model_copy(
                    settings.protocols.mrp, update=service.settings()
                )
                settings.protocols.mrp.identifier = service.identifier
            if service.protocol == Protocol.RAOP:
                settings.protocols.raop = model_copy(
                    settings.protocols.raop, update=service.settings()
                )
                settings.protocols.raop.identifier = service.identifier

    def __iter__(self) -> Iterator[Tuple[str, Any]]:
        """Iterate over stored devices."""
        # If settings are empty for a device (e.e. no settings overridden or credentials
        # saved), then the output will just be an empty dict. To not pollute the output
        # with those, we do some filtering here.
        dumped = self.storage_model.dict(exclude_defaults=True)
        dumped["devices"] = [device for device in dumped["devices"] if device != {}]
        return iter(dumped.items())

    def __repr__(self) -> str:
        """Return representation of MemoryStorage."""
        return str(self)
