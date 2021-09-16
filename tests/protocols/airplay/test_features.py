"""Unit tests for pyatv.protocols.airplay.features."""
import pytest

from pyatv.protocols.airplay.features import AirPlayFlags, parse


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
    assert parse(flags) == output


@pytest.mark.parametrize(
    "value",
    ["foo", "1234", "0x00000001,", ",0x00000001", "0x00000001,0x00000001,0x00000001"],
)
def test_bad_input(value):
    with pytest.raises(ValueError):
        parse(value)
