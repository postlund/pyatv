"""Unit tests for pyatv.protocols.airplay.features."""

import pytest

from pyatv.auth.hap_pairing import (
    NO_CREDENTIALS,
    TRANSIENT_CREDENTIALS,
    parse_credentials,
)
from pyatv.const import PairingRequirement, Protocol
from pyatv.core import MutableService
from pyatv.protocols.airplay.utils import (
    AirPlayFlags,
    AirPlayMajorVersion,
    get_pairing_requirement,
    get_protocol_version,
    is_password_required,
    is_remote_control_supported,
    parse_features,
)
from pyatv.settings import AirPlayVersion

# These are not really valid credentials but parse_credentials accepts them (for now)
HAP_CREDS = parse_credentials("aa:bb:cc:dd")
LEGACY_CREDS = parse_credentials(":aa::bb")


@pytest.mark.parametrize(
    "flags,output",
    [
        # Single feature flag
        ("0x00000001", AirPlayFlags.SupportsAirPlayVideoV1),
        (
            "0x40000003",
            AirPlayFlags.HasUnifiedAdvertiserInfo
            | AirPlayFlags.SupportsAirPlayPhoto
            | AirPlayFlags.SupportsAirPlayVideoV1,
        ),
        # Dual feature flag
        (
            "0x00000003,0x00000001",
            AirPlayFlags.IsCarPlay
            | AirPlayFlags.SupportsAirPlayPhoto
            | AirPlayFlags.SupportsAirPlayVideoV1,
        ),
    ],
)
def test_parse_features(flags, output):
    assert parse_features(flags) == output


@pytest.mark.parametrize(
    "value",
    ["foo", "1234", "0x00000001,", ",0x00000001", "0x00000001,0x00000001,0x00000001"],
)
def test_bad_input(value):
    with pytest.raises(ValueError):
        parse_features(value)


@pytest.mark.parametrize(
    "properties,requires_password",
    [
        ({}, False),
        ({"pw": "false"}, False),
        ({"pw": "true"}, True),
        ({"pw": "TRUE"}, True),
        ({"sf": "0x1"}, False),
        ({"sf": "0x80"}, True),
        ({"flags": "0x1"}, False),
        ({"flags": "0x80"}, True),
    ],
)
def test_is_password_required(properties, requires_password):
    service = MutableService("id", Protocol.RAOP, 0, properties)
    assert is_password_required(service) == requires_password


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "props,expected_req",
    [
        ({"sf": "0x1"}, PairingRequirement.NotNeeded),
        ({"sf": "0x200"}, PairingRequirement.Mandatory),
        ({"ft": "0x1"}, PairingRequirement.NotNeeded),
        ({"flags": "0x1"}, PairingRequirement.NotNeeded),
        ({"flags": "0x200"}, PairingRequirement.Mandatory),
        ({"features": "0x1"}, PairingRequirement.NotNeeded),
        ({"sf": "0x8"}, PairingRequirement.Mandatory),
        ({"flags": "0x8"}, PairingRequirement.Mandatory),
        ({"flags": "0x0"}, PairingRequirement.NotNeeded),
        # Corresponds to only allow "Current User", which is not
        # supported by pyatv right now
        ({"act": "2"}, PairingRequirement.Unsupported),
    ],
)
async def test_get_pairing_requirement(props, expected_req):
    service = MutableService("id", Protocol.AirPlay, 0, props)
    assert get_pairing_requirement(service) == expected_req


@pytest.mark.parametrize(
    "props,credentials,expected_supported",
    [
        ({}, NO_CREDENTIALS, False),
        ({"model": "AudioAccessory1,2"}, NO_CREDENTIALS, False),
        ({"model": "AudioAccessory1,2"}, TRANSIENT_CREDENTIALS, True),
        ({"model": "Foo"}, NO_CREDENTIALS, False),
        ({"osvers": "13.0"}, NO_CREDENTIALS, False),
        ({"osvers": "13.0", "model": "AppleTV5,6"}, NO_CREDENTIALS, False),
        ({"osvers": "13.0", "model": "AppleTV5,6"}, TRANSIENT_CREDENTIALS, False),
        ({"osvers": "13.0", "model": "AppleTV5,6"}, LEGACY_CREDS, False),
        ({"osvers": "13.0", "model": "AppleTV5,6"}, HAP_CREDS, True),
        ({"osvers": "8.4.4", "model": "AppleTV5,6"}, NO_CREDENTIALS, False),
    ],
)
def test_is_remote_control_supported(props, credentials, expected_supported):
    service = MutableService("id", Protocol.AirPlay, 0, props)
    assert is_remote_control_supported(service, credentials) == expected_supported


@pytest.mark.parametrize(
    "props, preferred_version, expected_version",
    [
        # Fallback
        ({}, AirPlayVersion.Auto, AirPlayMajorVersion.AirPlayV1),
        # Used by RAOP
        (
            {"ft": "0x5A7FFFF7,0xE"},
            AirPlayVersion.Auto,
            AirPlayMajorVersion.AirPlayV1,
        ),  # Apple TV 3
        (
            {"ft": "0x4A7FCA00,0xBC354BD0"},
            AirPlayVersion.Auto,
            AirPlayMajorVersion.AirPlayV2,
        ),  # HomePod Mini
        # Used by AirPlay
        (
            {"features": "0x5A7FFFF7,0xE"},
            AirPlayVersion.Auto,
            AirPlayMajorVersion.AirPlayV1,
        ),  # Apple TV 3
        # Should yield v1 but overridden with v2
        (
            {"features": "0x5A7FFFF7,0xE"},
            AirPlayVersion.V2,
            AirPlayMajorVersion.AirPlayV2,
        ),
        (
            {"features": "0x4A7FCA00,0xBC354BD0"},
            AirPlayVersion.Auto,
            AirPlayMajorVersion.AirPlayV2,
        ),  # HomePod Mini
        # Should yield v2 both overridden with v1
        (
            {"features": "0x4A7FCA00,0xBC354BD0"},
            AirPlayVersion.V1,
            AirPlayMajorVersion.AirPlayV1,
        ),
    ],
)
def test_get_protocol_version(props, preferred_version, expected_version):
    service = MutableService("id", Protocol.AirPlay, 0, props)
    assert get_protocol_version(service, preferred_version) == expected_version
