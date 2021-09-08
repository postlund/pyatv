"""Unit tests for pyatv.protocols.raop.raop."""

import pytest

from pyatv.exceptions import ProtocolError
from pyatv.protocols.raop.parsers import (
    EncryptionType,
    MetadataType,
    get_audio_properties,
    get_encryption_types,
    get_metadata_types,
)


@pytest.mark.parametrize(
    "properties,expected_sr,expected_ch,expected_ss",
    [
        ({}, 44100, 2, 2),
        ({"sr": "22050"}, 22050, 2, 2),
        ({"ch": "4"}, 44100, 4, 2),
        ({"ss": "32"}, 44100, 2, 4),
    ],
)
def test_parse_audio_properties(properties, expected_sr, expected_ch, expected_ss):
    sample_rate, channels, sample_size = get_audio_properties(properties)
    assert sample_rate == expected_sr
    assert channels == expected_ch
    assert sample_size == expected_ss


@pytest.mark.parametrize("properties", [{"sr": "abc"}, {"ch": "cde"}, {"ss": "fgh"}])
def test_parse_invalid_audio_property_raises(properties):
    with pytest.raises(ProtocolError):
        get_audio_properties(properties)


@pytest.mark.parametrize(
    "properties,expected",
    [
        ({"et": "0"}, EncryptionType.Unencrypted),
        ({"et": "1"}, EncryptionType.RSA),
        ({"et": "3"}, EncryptionType.FairPlay),
        ({"et": "4"}, EncryptionType.MFiSAP),
        ({"et": "5"}, EncryptionType.FairPlaySAPv25),
        ({"et": "0,1"}, EncryptionType.Unencrypted | EncryptionType.RSA),
    ],
)
def test_parse_encryption_type(properties, expected):
    assert get_encryption_types(properties) == expected


@pytest.mark.parametrize(
    "properties",
    [
        ({}),
        ({"et": ""}),
        ({"et": "foobar"}),
    ],
)
def test_parse_encryption_bad_types(properties):
    assert get_encryption_types(properties) == EncryptionType.Unknown


def test_parse_encryption_include_unknown_type():
    assert (
        get_encryption_types({"et": "0,1000"})
        == EncryptionType.Unknown | EncryptionType.Unencrypted
    )


@pytest.mark.parametrize(
    "properties,expected",
    [
        ({}, MetadataType.NotSupported),
        ({"md": "0"}, MetadataType.Text),
        ({"md": "1"}, MetadataType.Artwork),
        (
            {"md": "0,1,2"},
            MetadataType.Text | MetadataType.Artwork | MetadataType.Progress,
        ),
    ],
)
def test_parse_metadata_types(properties, expected):
    assert get_metadata_types(properties) == expected
