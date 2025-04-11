"""Settings for configuring pyatv."""

from enum import Enum
import os
import re
from typing import Optional

from pyatv.support.pydantic_compat import BaseModel, Field, field_validator

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


DEFAULT_NAME = "pyatv"
DEFUALT_MAC = "02:70:79:61:74:76"  # Locally administrated (02) + "pyatv" in hex
DEFAULT_DEVICE_ID = "FF:70:79:61:74:76"  # 0xFF + "pyatv"
DEFAULT_RP_ID = "cafecafecafe"
DEFAULT_MODEL = "iPhone10,6"
DEFAULT_OS_NAME = "iPhone OS"
DEFAULT_OS_BUILD = "18G82"
DEFAULT_OS_VERSION = "14.7.1"

# pylint: disable=invalid-name


class AirPlayVersion(str, Enum):
    """AirPlay version to use."""

    Auto = "auto"
    """Automatically determine what version to use."""

    V1 = "1"
    """Use version 1 of AirPlay."""

    V2 = "2"
    """Use version 2 of AirPlay."""


class MrpTunnel(str, Enum):
    """How MRP tunneling over AirPlay is handled."""

    Auto = "auto"
    """Automatically set up MRP tunnel if supported by remote device."""

    Force = "force"
    """Force set up of MRP tunnel even if remote device does not supports it."""

    Disable = "disable"
    """Fully disable set up of MRP tunnel."""


# pylint: enable=invalid-name


class InfoSettings(BaseModel, extra="ignore"):  # type: ignore[call-arg]
    """Information related settings."""

    name: str = DEFAULT_NAME
    mac: str = DEFUALT_MAC
    model: str = DEFAULT_MODEL
    device_id: str = DEFAULT_DEVICE_ID
    rp_id: Optional[str] = None
    os_name: str = DEFAULT_OS_NAME
    os_build: str = DEFAULT_OS_BUILD
    os_version: str = DEFAULT_OS_VERSION

    @field_validator("mac")
    @classmethod
    def mac_validator(cls, mac: str) -> str:
        """Validate MAC address to be correct."""
        if re.match(_MAC_REGEX, mac) is None:
            raise ValueError(f"{mac} is not a valid MAC address")
        return mac

    @field_validator("rp_id", always=True)
    @classmethod
    def fill_missing_rp_id(cls, v):
        """Generate a new random rp_id if it is missing."""
        if v is None:
            return os.urandom(6).hex()
        return v


class AirPlaySettings(BaseModel, extra="ignore"):  # type: ignore[call-arg]
    """Settings related to AirPlay."""

    identifier: Optional[str] = None
    credentials: Optional[str] = None
    password: Optional[str] = None

    mrp_tunnel: MrpTunnel = MrpTunnel.Auto


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

    protocol_version: AirPlayVersion = AirPlayVersion.Auto
    """Protocol version used.

    In reality this corresponds to the AirPlay version used. Set to 0 for automatic
    mode (recommended), or 1 or 2 for AirPlay 1 or 2 respectively.
    """

    timing_port: int = 0
    """Server side (UDP) port used by timing server.

    Set to 0 to use random free port.
    """

    control_port: int = 0
    """Server side (UDP) port used by control server.

    Set to 0 to use random free port.
    """


class ProtocolSettings(BaseModel, extra="ignore"):  # type: ignore[call-arg]
    """Container for protocol specific settings."""

    airplay: AirPlaySettings = Field(default_factory=AirPlaySettings)
    companion: CompanionSettings = Field(default_factory=CompanionSettings)
    dmap: DmapSettings = Field(default_factory=DmapSettings)
    mrp: MrpSettings = Field(default_factory=MrpSettings)
    raop: RaopSettings = Field(default_factory=RaopSettings)


class Settings(BaseModel, extra="ignore"):  # type: ignore[call-arg]
    """Settings container class."""

    info: InfoSettings = Field(default_factory=InfoSettings)
    protocols: ProtocolSettings = Field(default_factory=ProtocolSettings)
