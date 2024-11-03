"""Unit tests for pyatv.support.device_info."""

import pytest

from pyatv.const import DeviceModel, OperatingSystem
from pyatv.support.device_info import (
    lookup_internal_name,
    lookup_model,
    lookup_os,
    lookup_version,
)


@pytest.mark.parametrize(
    "model_str,expected_model",
    [
        ("AppleTV6,2", DeviceModel.Gen4K),
        ("AudioAccessory5,1", DeviceModel.HomePodMini),
        ("bad_model", DeviceModel.Unknown),
    ],
)
def test_lookup_model(model_str, expected_model):
    assert lookup_model(model_str) == expected_model


@pytest.mark.parametrize(
    "internal_name,expected_model",
    [
        ("J105aAP", DeviceModel.Gen4K),
        ("bad_name", DeviceModel.Unknown),
    ],
)
def test_lookup_internal_name(internal_name, expected_model):
    assert lookup_internal_name(internal_name) == expected_model


@pytest.mark.parametrize(
    "version,expected_version",
    [
        (None, None),
        ("17J586", "13.0"),
        ("bad_version", None),
        ("16F123", "12.x"),
        ("17F123", "13.x"),
    ],
)
def test_lookup_existing_version(version, expected_version):
    assert lookup_version(version) == expected_version


@pytest.mark.parametrize(
    "id_or_model,expected_os",
    [
        ("bad", OperatingSystem.Unknown),
        ("MacBookAir10,1", OperatingSystem.MacOS),
        ("iMac1,2", OperatingSystem.MacOS),
        ("Macmini1,1", OperatingSystem.MacOS),
        ("MacBookPro5,67", OperatingSystem.MacOS),
        ("Mac1,4", OperatingSystem.MacOS),
        ("MacPro19,4", OperatingSystem.MacOS),
        (DeviceModel.AirPortExpress, OperatingSystem.AirPortOS),
        (DeviceModel.AirPortExpressGen2, OperatingSystem.AirPortOS),
        (DeviceModel.HomePod, OperatingSystem.TvOS),
        (DeviceModel.HomePodGen2, OperatingSystem.TvOS),
        (DeviceModel.HomePodMini, OperatingSystem.TvOS),
        (DeviceModel.AppleTVGen1, OperatingSystem.Legacy),
        (DeviceModel.Gen2, OperatingSystem.Legacy),
        (DeviceModel.Gen3, OperatingSystem.Legacy),
        (DeviceModel.Gen4, OperatingSystem.TvOS),
        (DeviceModel.Gen4K, OperatingSystem.TvOS),
        (DeviceModel.AppleTV4KGen2, OperatingSystem.TvOS),
        (DeviceModel.AppleTV4KGen3, OperatingSystem.TvOS),
    ],
)
def test_lookup_os(id_or_model, expected_os):
    assert lookup_os(id_or_model) == expected_os
