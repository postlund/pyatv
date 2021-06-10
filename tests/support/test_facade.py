"""Unit tests for pyatv.support.facade."""
import inspect
from ipaddress import IPv4Address

import pytest

from pyatv import exceptions
from pyatv.conf import AppleTV
from pyatv.const import FeatureName, Protocol
from pyatv.interface import (
    Audio,
    FeatureInfo,
    Features,
    FeatureState,
    Power,
    PushUpdater,
)
from pyatv.support.facade import FacadeAppleTV, SetupData


@pytest.fixture(name="facade_dummy")
def facade_dummy_fixture(session_manager):
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


class DummyPushUpdater(PushUpdater):
    def __init__(self, loop):
        super().__init__(loop)

    @property
    def active(self) -> bool:
        return False

    def start(self, initial_delay: int = 0) -> None:
        raise exceptions.NotSupportedError

    def stop(self) -> None:
        raise exceptions.NotSupportedError


class DummyPower(Power):
    def __init__(self) -> None:
        self.turn_on_called = False
        self.turn_off_called = False

    async def turn_on(self, await_new_state: bool = False) -> None:
        self.turn_on_called = True

    async def turn_off(self, await_new_state: bool = False) -> None:
        self.turn_off_called = True


class DummyAudio(Audio):
    def __init__(self, volume: float) -> None:
        self._volume = volume

    @property
    def volume(self) -> float:
        return self._volume

    async def set_volume(self, level: float) -> None:
        self._volume = volume


@pytest.fixture(name="register_interface")
def register_interface_fixture(facade_dummy):
    def _register_func(feature: FeatureName, instance, protocol: Protocol):
        interface = inspect.getmro(type(instance))[1]
        sdg = SetupDataGenerator(feature)
        facade_dummy.interfaces[interface].register(instance, protocol)
        facade_dummy.add_protocol(protocol, sdg.get_setup_data())
        return instance

    yield _register_func


@pytest.mark.asyncio
async def test_connect_with_no_protocol(facade_dummy):
    with pytest.raises(exceptions.NoServiceError):
        await facade_dummy.connect()


def test_features_multi_instances(facade_dummy, register_interface):
    register_interface(FeatureName.Play, DummyFeatures(FeatureName.Play), Protocol.DMAP)
    register_interface(
        FeatureName.Pause, DummyFeatures(FeatureName.Pause), Protocol.MRP
    )

    feat = facade_dummy.features

    # State from MRP
    assert feat.get_feature(FeatureName.Pause).state == FeatureState.Available

    # State from DMAP
    assert feat.get_feature(FeatureName.Play).state == FeatureState.Available

    # Default state with no instance
    assert feat.get_feature(FeatureName.PlayUrl).state == FeatureState.Unsupported


def test_features_feature_overlap_uses_priority(facade_dummy, register_interface):
    # Pause available for DMAP but not MRP -> pause is unavailable because MRP prio
    register_interface(
        FeatureName.Pause,
        DummyFeatures(FeatureName.Pause, FeatureState.Unavailable),
        Protocol.MRP,
    )
    register_interface(
        FeatureName.Pause, DummyFeatures(FeatureName.Pause), Protocol.DMAP
    )

    assert (
        facade_dummy.features.get_feature(FeatureName.Pause).state
        == FeatureState.Unavailable
    )


def test_features_push_updates(facade_dummy, event_loop, register_interface):
    feat = facade_dummy.features

    assert feat.get_feature(FeatureName.PushUpdates).state == FeatureState.Unsupported

    register_interface(
        FeatureName.PushUpdates, DummyPushUpdater(event_loop), Protocol.MRP
    )

    assert feat.get_feature(FeatureName.PushUpdates).state == FeatureState.Available


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "feature,func", [(FeatureName.TurnOn, "turn_on"), (FeatureName.TurnOff, "turn_off")]
)
async def test_power_prefer_companion(feature, func, facade_dummy, register_interface):
    power_mrp = register_interface(feature, DummyPower(), Protocol.MRP)
    power_comp = register_interface(feature, DummyPower(), Protocol.Companion)

    await getattr(facade_dummy.power, func)()

    assert not getattr(power_mrp, f"{func}_called")
    assert getattr(power_comp, f"{func}_called")


@pytest.mark.parametrize("volume", [-0.1, 100.1])
async def test_audio_get_volume_out_of_range(facade_dummy, register_interface, volume):
    register_interface(FeatureName.Volume, DummyAudio(volume), Protocol.RAOP)

    with pytest.raises(exceptions.ProtocolError):
        facade_dummy.audio.volume


@pytest.mark.parametrize("volume", [-0.1, 100.1])
async def test_audio_set_volume_out_of_range(facade_dummy, register_interface, volume):
    register_interface(FeatureName.Volume, DummyAudio(volume), Protocol.RAOP)

    with pytest.raises(exceptions.ProtocolError):
        await facade_dummy.audio.set_volume(volume)
