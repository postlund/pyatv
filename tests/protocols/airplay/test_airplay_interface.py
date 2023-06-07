"""Unit tests for interface implementations in pyatv.protocols.airplay."""

import pytest

from pyatv.const import FeatureName, FeatureState
from pyatv.protocols.airplay import AirPlayFeatures
from pyatv.protocols.airplay.utils import parse_features

# AirPlayFeatures


@pytest.mark.parametrize(
    "flags,expected_state",
    [
        ("0x0,0x0", FeatureState.Unavailable),
        ("0x1,0x0", FeatureState.Available),  # VideoV1
        ("0x00000000,0x20000", FeatureState.Available),  # VideoV2
    ],
)
def test_feature_play_url(flags, expected_state):
    features = AirPlayFeatures(parse_features(flags))
    assert features.get_feature(FeatureName.PlayUrl).state == expected_state
