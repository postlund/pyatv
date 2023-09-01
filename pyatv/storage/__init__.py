"""Storage module."""
from hashlib import sha256
from typing import List, Sequence

from pydantic import BaseModel

from pyatv.const import Protocol
from pyatv.exceptions import DeviceIdMissingError, SettingsError
from pyatv.interface import BaseConfig, Storage
from pyatv.settings import Settings

__pdoc_dev_page__ = "/development/storage"

__pdoc__ = {
    "StorageModel.model_config": False,
    "StorageModel.model_fields": False,
}

MODEL_VERSION = 1


def _calculate_settings_hash(settings: List[Settings]) -> str:
    # Calculate a hash of all settings by dumping content to JSON and hashing all
    # output using SHA256 (arbitrarily chosen for now). This is not very efficient
    # (especially when making multiple calls) but should be reliable and good enough.
    hasher = sha256()
    for setting in settings:
        setting_json = setting.model_dump_json(exclude_defaults=True)
        hasher.update(setting_json.encode("utf-8"))
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
        self._settings_hash: str = _calculate_settings_hash(self._settings)

    @property
    def changed(self) -> bool:
        """Return if anything has changed in the model since loading.

        This property will return True if a any setting has been changed. It is reset
        when data is loaded into storage (by calling load) or manually by calling
        mark_as_solved (typically done by save).
        """
        return self._settings_hash != _calculate_settings_hash(self._settings)

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

    def mark_as_saved(self) -> None:
        """Call after saving to indicate settings have been saved.

        The changed property reflects whether something has been changed in the model
        or not based on calling this method.
        """
        self._settings_hash = _calculate_settings_hash(self._settings)

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
                settings.protocols.airplay = settings.protocols.airplay.model_copy(
                    update=service.settings()
                )
                settings.protocols.airplay.identifier = service.identifier
            elif service.protocol == Protocol.DMAP:
                settings.protocols.dmap = settings.protocols.dmap.model_copy(
                    update=service.settings()
                )
                settings.protocols.dmap.identifier = service.identifier
            elif service.protocol == Protocol.Companion:
                settings.protocols.companion = settings.protocols.companion.model_copy(
                    update=service.settings()
                )
                settings.protocols.companion.identifier = service.identifier
            elif service.protocol == Protocol.MRP:
                settings.protocols.mrp = settings.protocols.mrp.model_copy(
                    update=service.settings()
                )
                settings.protocols.mrp.identifier = service.identifier
            if service.protocol == Protocol.RAOP:
                settings.protocols.raop = settings.protocols.raop.model_copy(
                    update=service.settings()
                )
                settings.protocols.raop.identifier = service.identifier

    def __repr__(self) -> str:
        """Return representation of MemoryStorage."""
        return str(self)
