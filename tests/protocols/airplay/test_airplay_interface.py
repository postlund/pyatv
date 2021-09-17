"""Unit tests for interface implementations in pyatv.protocols.airplay."""

import pytest

from pyatv.conf import ManualService
from pyatv.const import FeatureName, FeatureState, Protocol
from pyatv.protocols.airplay import AirPlayFeatures

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
    service = ManualService("id", Protocol.AirPlay, 0, {"features": flags})
    features = AirPlayFeatures(service)
    assert features.get_feature(FeatureName.PlayUrl).state == expected_state
