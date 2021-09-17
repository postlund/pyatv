"""Unit tests for pyatv.protocols.airplay.features."""
import pytest

from pyatv.const import Protocol
from pyatv.core import MutableService
from pyatv.protocols.airplay.utils import (
    AirPlayFlags,
    is_password_required,
    parse_features,
)


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
