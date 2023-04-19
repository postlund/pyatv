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
    get_pairing_requirement,
    is_password_required,
    is_remote_control_supported,
    parse_features,
)

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
