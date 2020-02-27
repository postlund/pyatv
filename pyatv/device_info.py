"""Lookup methods for device data."""

import re

from pyatv.const import DeviceModel


_MODEL_LIST = {
    'AppleTV2,1': DeviceModel.Gen2,
    'AppleTV3,1': DeviceModel.Gen3,
    'AppleTV3,2': DeviceModel.Gen3,
    'AppleTV5,3': DeviceModel.Gen4,
    'AppleTV6,2': DeviceModel.Gen4K,
    }


# Incomplete list here!
_VERSION_LIST = {
    '17J586': '13.0',
    '17K82': '13.2',
    '17K449': '13.3',
    '17K795': '13.3.1',
    }


def lookup_model(identifier):
    """Lookup device model from identifier."""
    return _MODEL_LIST.get(identifier, DeviceModel.Unknown)


def lookup_version(build):
    """Lookup OS version from build."""
    if not build:
        return None

    version = _VERSION_LIST.get(build)
    if version:
        return version

    match = re.match(r'^(\d+)[A-Z]', build)
    if match:
        base = int(match.groups()[0])

        # 17A123 corresponds to tvOS 13.x, 16A123 to tvOS 12.x and so on
        return str(base - 4) + '.x'

    return None
