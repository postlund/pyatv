"""Unit tests for pyatv.support.facade."""
from ipaddress import IPv4Address

import pytest

from pyatv.conf import AppleTV
from pyatv.const import FeatureName, Protocol
from pyatv.interface import FeatureInfo, Features, FeatureState
from pyatv.support.facade import FacadeAppleTV, SetupData


@pytest.fixture
def facade_dummy(session_manager):
    conf = AppleTV(IPv4Address("127.0.0.1"), "Test")
    facade = FacadeAppleTV(conf, session_manager)
    yield facade


class SetupDataGenerator:
    def __init__(self, *features):
        self.connect_called = False
        self.close_called = False
        self.features = set(features)

    async def connect(self):
        self.connect_called = True

    def close(self):
        self.close_called = True

    def get_setup_data(self) -> SetupData:
        return self.connect, self.close, self.features


class DummyFeatures(Features):
    def __init__(self, feature_name, feature_state=FeatureState.Available):
        self.feature_name = feature_name
        self.feature_state = feature_state

    def get_feature(self, feature_name: FeatureName) -> FeatureInfo:
        return FeatureInfo(
            self.feature_state
            if feature_name == self.feature_name
            else FeatureState.Unsupported
        )


def test_features_multi_instances(facade_dummy):
    mrp_sdg = SetupDataGenerator(FeatureName.Pause)
    mrp_features = DummyFeatures(FeatureName.Pause)

    dmap_sdg = SetupDataGenerator(FeatureName.Play)
    dmap_features = DummyFeatures(FeatureName.Play)

    facade_dummy.interfaces[Features].register(mrp_features, Protocol.MRP)
    facade_dummy.interfaces[Features].register(dmap_features, Protocol.DMAP)

    facade_dummy.add_protocol(Protocol.MRP, mrp_sdg.get_setup_data())
    facade_dummy.add_protocol(Protocol.DMAP, dmap_sdg.get_setup_data())

    # State from MRP
    assert (
        facade_dummy.features.get_feature(FeatureName.Pause).state
        == FeatureState.Available
    )

    # State from DMAP
    assert (
        facade_dummy.features.get_feature(FeatureName.Play).state
        == FeatureState.Available
    )

    # Default state with no instance
    assert (
        facade_dummy.features.get_feature(FeatureName.PlayUrl).state
        == FeatureState.Unsupported
    )


def test_features_feature_overlap_uses_priority(facade_dummy):
    sdg = SetupDataGenerator(FeatureName.Pause)
    mrp_features = DummyFeatures(FeatureName.Pause, FeatureState.Unavailable)
    dmap_features = DummyFeatures(FeatureName.Pause)

    facade_dummy.interfaces[Features].register(mrp_features, Protocol.MRP)
    facade_dummy.interfaces[Features].register(dmap_features, Protocol.DMAP)

    facade_dummy.add_protocol(Protocol.MRP, sdg.get_setup_data())
    facade_dummy.add_protocol(Protocol.DMAP, sdg.get_setup_data())

    assert (
        facade_dummy.features.get_feature(FeatureName.Pause).state
        == FeatureState.Unavailable
    )
