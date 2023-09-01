"""Settings for configuring pyatv."""
import re
from typing import Optional

from pydantic import BaseModel, Field
from pydantic.functional_validators import AfterValidator
from pydantic_settings import BaseSettings
from typing_extensions import Annotated

__pdoc__ = {
    "InfoSettings.model_config": False,
    "InfoSettings.model_fields": False,
    "AirPlaySettings.model_config": False,
    "AirPlaySettings.model_fields": False,
    "CompanionSettings.model_config": False,
    "CompanionSettings.model_fields": False,
    "DmapSettings.model_config": False,
    "DmapSettings.model_fields": False,
    "MrpSettings.model_config": False,
    "MrpSettings.model_fields": False,
    "RaopSettings.model_config": False,
    "RaopSettings.model_fields": False,
    "ProtocolSettings.model_config": False,
    "ProtocolSettings.model_fields": False,
    "Settings.model_config": False,
    "Settings.model_fields": False,
}

__pdoc_dev_page__ = "/development/storage"


# TODO: Replace with pydantic-extra-types when a release is out with MAC
#       address validation included
_MAC_REGEX = r"[0-9a-fA-F]{2}(:[0-9a-fA-F]{2}){5}"


def _mac_validator(mac_addr: str) -> str:
    assert (
        re.match(_MAC_REGEX, mac_addr) is not None
    ), f"{mac_addr} is not a valid MAC address"
    return mac_addr


MacAddress = Annotated[str, AfterValidator(_mac_validator)]

DEFAULT_NAME = "pyatv"
DEFUALT_MAC = "02:70:79:61:74:76"  # Locally administrated (02) + "pyatv" in hex
DEFAULT_DEVICE_ID = "FF:70:79:61:74:76"  # 0xFF + "pyatv"
DEFAULT_MODEL = "iPhone10,6"
DEFAULT_OS_NAME = "iPhone OS"
DEFAULT_OS_BUILD = "18G82"
DEFAULT_OS_VERSION = "14.7.1"


class InfoSettings(BaseModel, extra="ignore"):  # type: ignore[call-arg]
    """Information related settings."""

    name: str = DEFAULT_NAME
    mac: MacAddress = DEFUALT_MAC
    model: str = DEFAULT_MODEL
    device_id: str = DEFAULT_DEVICE_ID
    os_name: str = DEFAULT_OS_NAME
    os_build: str = DEFAULT_OS_BUILD
    os_version: str = DEFAULT_OS_VERSION


class AirPlaySettings(BaseModel, extra="ignore"):  # type: ignore[call-arg]
    """Settings related to AirPlay."""

    identifier: Optional[str] = None
    credentials: Optional[str] = None
    password: Optional[str] = None


class CompanionSettings(BaseModel, extra="ignore"):  # type: ignore[call-arg]
    """Settings related to Companion."""

    identifier: Optional[str] = None
    credentials: Optional[str] = None


class DmapSettings(BaseModel, extra="ignore"):  # type: ignore[call-arg]
    """Settings related to DMAP."""

    identifier: Optional[str] = None
    credentials: Optional[str] = None


class MrpSettings(BaseModel, extra="ignore"):  # type: ignore[call-arg]
    """Settings related to MRP."""

    identifier: Optional[str] = None
    credentials: Optional[str] = None


class RaopSettings(BaseModel, extra="ignore"):  # type: ignore[call-arg]
    """Settings related to RAOP."""

    identifier: Optional[str] = None
    credentials: Optional[str] = None
    password: Optional[str] = None


class ProtocolSettings(BaseModel, extra="ignore"):  # type: ignore[call-arg]
    """Container for protocol specific settings."""

    airplay: AirPlaySettings = Field(default_factory=AirPlaySettings)
    companion: CompanionSettings = Field(default_factory=CompanionSettings)
    dmap: DmapSettings = Field(default_factory=DmapSettings)
    mrp: MrpSettings = Field(default_factory=MrpSettings)
    raop: RaopSettings = Field(default_factory=RaopSettings)


class Settings(BaseSettings, extra="ignore"):  # type: ignore[call-arg]
    """Settings container class."""

    info: InfoSettings = Field(default_factory=InfoSettings)
    protocols: ProtocolSettings = Field(default_factory=ProtocolSettings)
