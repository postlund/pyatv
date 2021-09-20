"""Unit tests for pyatv.support.device_info."""

from pyatv.const import DeviceModel
from pyatv.support.device_info import lookup_internal_name, lookup_model, lookup_version


def test_lookup_existing_model():
    assert lookup_model("AppleTV6,2") == DeviceModel.Gen4K


def test_lookup_homepod():
    assert lookup_model("AudioAccessory5,1") == DeviceModel.HomePodMini


def test_lookup_missing_model():
    assert lookup_model("bad_model") == DeviceModel.Unknown


def test_lookup_existing_internal_name():
    assert lookup_internal_name("J105aAP") == DeviceModel.Gen4K


def test_lookup_missing_internal_name():
    assert lookup_internal_name("bad_name") == DeviceModel.Unknown


def test_lookup_existing_version():
    assert lookup_version("17J586") == "13.0"


def test_lookup_bad_version():
    assert not lookup_version(None)
    assert not lookup_version("bad_version")


def test_lookup_guess_major_version():
    assert lookup_version("16F123") == "12.x"
    assert lookup_version("17F123") == "13.x"
