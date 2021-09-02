"""Lookup methods for device data."""

import re
from typing import Dict, Optional

from pyatv.const import DeviceModel

_MODEL_LIST: Dict[str, DeviceModel] = {
    "AirPort4,107": DeviceModel.AirPortExpress,
    "AirPort10,115": DeviceModel.AirPortExpressGen2,
    "AppleTV2,1": DeviceModel.Gen2,
    "AppleTV3,1": DeviceModel.Gen3,
    "AppleTV3,2": DeviceModel.Gen3,
    "AppleTV5,3": DeviceModel.Gen4,
    "AppleTV6,2": DeviceModel.Gen4K,
    "AppleTV11,1": DeviceModel.AppleTV4KGen2,
    "AudioAccessory1,1": DeviceModel.HomePod,
    "AudioAccessory1,2": DeviceModel.HomePod,
    "AudioAccessory5,1": DeviceModel.HomePodMini,
}


_INTERNAL_NAME_LIST: Dict[str, DeviceModel] = {
    "K66AP": DeviceModel.Gen2,
    "J33AP": DeviceModel.Gen3,
    "J33IAP": DeviceModel.Gen3,
    "J42dAP": DeviceModel.Gen4,
    "J105aAP": DeviceModel.Gen4K,
    "J305AP": DeviceModel.AppleTV4KGen2,
}

# Incomplete list here! Only Apple TV version numbers for now.
_VERSION_LIST: Dict[str, str] = {
    "17J586": "13.0",
    "17K82": "13.2",
    "17K449": "13.3",
    "17K795": "13.3.1",
    "17L256": "13.4",
    "17L562": "13.4.5",
    "17L570": "13.4.6",
    "17M61": "13.4.8",
    "18J386": "14.0",
    "18J400": "14.0.1",
    "18J411": "14.0.2",
    "18K57": "14.2",
    "18K561": "14.3",
    "18K802": "14.4",
    "18L204": "14.5",
    "18L569": "14.6",
    "18M60": "14.7",
}


def lookup_model(identifier: Optional[str]) -> DeviceModel:
    """Lookup device model from identifier."""
    return _MODEL_LIST.get(identifier or "", DeviceModel.Unknown)


def lookup_internal_name(name: Optional[str]) -> DeviceModel:
    """Lookup device model from internal Apple model name."""
    return _INTERNAL_NAME_LIST.get(name or "", DeviceModel.Unknown)


def lookup_version(build: Optional[str]) -> Optional[str]:
    """Lookup OS version from build."""
    if not build:
        return None

    version = _VERSION_LIST.get(build or "")
    if version:
        return version

    match = re.match(r"^(\d+)[A-Z]", build)
    if match:
        base = int(match.groups()[0])

        # 17A123 corresponds to tvOS 13.x, 16A123 to tvOS 12.x and so on
        return str(base - 4) + ".x"

    return None
