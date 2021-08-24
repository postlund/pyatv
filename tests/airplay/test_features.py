"""Unit tests for pyatv.airplay.features."""
import pytest

from pyatv.airplay.features import AirPlayFeatures, parse


@pytest.mark.parametrize(
    "flags,output",
    [
        # Single feature flag
        ("0x00000001", AirPlayFeatures.SupportsAirPlayVideoV1),
        (
            "0x40000003",
            AirPlayFeatures.HasUnifiedAdvertiserInfo
            | AirPlayFeatures.SupportsAirPlayPhoto
            | AirPlayFeatures.SupportsAirPlayVideoV1,
        ),
        # Dual feature flag
        (
            "0x00000003,0x00000001",
            AirPlayFeatures.IsCarPlay
            | AirPlayFeatures.SupportsAirPlayPhoto
            | AirPlayFeatures.SupportsAirPlayVideoV1,
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
