"""Unit tests for pyatv.core.facade."""
import asyncio
import inspect
from ipaddress import IPv4Address
from typing import Any, Dict, Set
from unittest.mock import MagicMock

import pytest

from pyatv import exceptions
from pyatv.conf import AppleTV
from pyatv.const import FeatureName, OperatingSystem, Protocol
from pyatv.core import SetupData
from pyatv.core.facade import FacadeAppleTV, SetupData
from pyatv.interface import (
    Audio,
    DeviceInfo,
    DeviceListener,
    FeatureInfo,
    Features,
    FeatureState,
    Power,
    PushUpdater,
    Stream,
)

TEST_URL = "http://test"

pytestmark = pytest.mark.asyncio


@pytest.fixture(name="facade_dummy")
def facade_dummy_fixture(session_manager):
    conf = AppleTV(IPv4Address("127.0.0.1"), "Test")
    facade = FacadeAppleTV(conf, session_manager)
    yield facade


class SetupDataGenerator:
    def __init__(self, protocol, *features):
        self.protocol = protocol
        self.connect_called: bool = False
        self.close_called: bool = False
        self.close_calls: int = 0
        self.interfaces: Mapping[Any, Any] = {}
        self.features: set = set(features)
        self.pending_tasks: set = set()
        self.connect_succeeded = True
        self.device_info = {}

    async def connect(self):
        self.connect_called = True
        return self.connect_succeeded

    def close(self):
        self.close_called = True
        self.close_calls += 1
        return self.pending_tasks

    def get_setup_data(self) -> SetupData:
        return SetupData(
            self.protocol,
            self.connect,
            self.close,
            lambda: self.device_info,
            self.interfaces,
            self.features,
        )


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


class DummyDeviceListener(DeviceListener):
    def __init__(self):
        self.lost_calls: int = 0
        self.closed_calls: int = 0

    def connection_lost(self, exception: Exception) -> None:
        self.lost_calls += 1

    def connection_closed(self) -> None:
        self.closed_calls += 1


class DummyStream(Stream):
    def __init__(self) -> None:
        self.url = None

    async def play_url(self, url: str, **kwargs) -> None:
        self.url = url


@pytest.fixture(name="register_interface")
def register_interface_fixture(facade_dummy):
    def _register_func(feature: FeatureName, instance, protocol: Protocol):
        interface = inspect.getmro(type(instance))[1]
        sdg = SetupDataGenerator(protocol, feature)
        sdg.interfaces[interface] = instance
        facade_dummy.add_protocol(sdg.get_setup_data())
        return instance, sdg

    yield _register_func


async def test_connect_with_no_protocol(facade_dummy):
    with pytest.raises(exceptions.NoServiceError):
        await facade_dummy.connect()


async def test_connect_again_raises(facade_dummy, register_interface):
    register_interface(FeatureName.Play, DummyFeatures(FeatureName.Play), Protocol.DMAP)
    await facade_dummy.connect()

    with pytest.raises(exceptions.InvalidStateError):
        await facade_dummy.connect()


async def test_add_after_connect_raises(facade_dummy, register_interface):
    feat = facade_dummy.features

    register_interface(FeatureName.Play, DummyFeatures(FeatureName.Play), Protocol.DMAP)
    assert feat.get_feature(FeatureName.Play).state == FeatureState.Unsupported

    await facade_dummy.connect()

    assert feat.get_feature(FeatureName.Play).state == FeatureState.Available


async def test_interface_not_exposed_prior_to_connect(facade_dummy, register_interface):
    register_interface(FeatureName.Play, DummyFeatures(FeatureName.Play), Protocol.DMAP)

    await facade_dummy.connect()


async def test_features_multi_instances(facade_dummy, register_interface):
    register_interface(FeatureName.Play, DummyFeatures(FeatureName.Play), Protocol.DMAP)
    register_interface(
        FeatureName.Pause, DummyFeatures(FeatureName.Pause), Protocol.MRP
    )

    await facade_dummy.connect()
    feat = facade_dummy.features

    # State from MRP
    assert feat.get_feature(FeatureName.Pause).state == FeatureState.Available

    # State from DMAP
    assert feat.get_feature(FeatureName.Play).state == FeatureState.Available

    # Default state with no instance
    assert feat.get_feature(FeatureName.PlayUrl).state == FeatureState.Unsupported


async def test_ignore_already_connected_protocol(facade_dummy, register_interface):
    register_interface(FeatureName.Play, DummyFeatures(FeatureName.Play), Protocol.DMAP)
    register_interface(
        FeatureName.Pause, DummyFeatures(FeatureName.Pause), Protocol.DMAP
    )

    await facade_dummy.connect()
    feat = facade_dummy.features

    assert feat.get_feature(FeatureName.Play).state == FeatureState.Available

    # As DMAP was already added with Play as supported, the second instance should be
    # ignored (this not affecting state)
    assert feat.get_feature(FeatureName.Pause).state == FeatureState.Unsupported


async def test_features_feature_overlap_uses_priority(facade_dummy, register_interface):
    # Pause available for DMAP but not MRP -> pause is unavailable because MRP prio
    register_interface(
        FeatureName.Pause,
        DummyFeatures(FeatureName.Pause, FeatureState.Unavailable),
        Protocol.MRP,
    )
    register_interface(
        FeatureName.Pause, DummyFeatures(FeatureName.Pause), Protocol.DMAP
    )

    await facade_dummy.connect()
    assert (
        facade_dummy.features.get_feature(FeatureName.Pause).state
        == FeatureState.Unavailable
    )


async def test_features_push_updates(facade_dummy, event_loop, register_interface):
    feat = facade_dummy.features

    assert feat.get_feature(FeatureName.PushUpdates).state == FeatureState.Unsupported

    register_interface(
        FeatureName.PushUpdates, DummyPushUpdater(event_loop), Protocol.MRP
    )

    await facade_dummy.connect()
    assert feat.get_feature(FeatureName.PushUpdates).state == FeatureState.Available


@pytest.mark.parametrize(
    "feature,func", [(FeatureName.TurnOn, "turn_on"), (FeatureName.TurnOff, "turn_off")]
)
async def test_power_prefer_companion(feature, func, facade_dummy, register_interface):
    power_mrp, _ = register_interface(feature, DummyPower(), Protocol.MRP)
    power_comp, _ = register_interface(feature, DummyPower(), Protocol.Companion)

    await facade_dummy.connect()
    await getattr(facade_dummy.power, func)()

    assert not getattr(power_mrp, f"{func}_called")
    assert getattr(power_comp, f"{func}_called")


@pytest.mark.parametrize("volume", [-0.1, 100.1])
async def test_audio_get_volume_out_of_range(facade_dummy, register_interface, volume):
    register_interface(FeatureName.Volume, DummyAudio(volume), Protocol.RAOP)

    await facade_dummy.connect()

    with pytest.raises(exceptions.ProtocolError):
        facade_dummy.audio.volume


@pytest.mark.parametrize("volume", [-0.1, 100.1])
async def test_audio_set_volume_out_of_range(facade_dummy, register_interface, volume):
    register_interface(FeatureName.Volume, DummyAudio(volume), Protocol.RAOP)

    with pytest.raises(exceptions.ProtocolError):
        await facade_dummy.audio.set_volume(volume)


async def test_close_pending_tasks(facade_dummy, session_manager):
    obj = MagicMock()
    obj.called = False

    async def connect() -> bool:
        return True

    def close() -> Set[asyncio.Task]:
        async def close_task() -> None:
            obj.called = True

        return set([asyncio.ensure_future(close_task())])

    def device_info() -> Dict[str, Any]:
        return {}

    facade_dummy.add_protocol(
        SetupData(
            Protocol.DMAP,
            connect,
            close,
            device_info,
            {Power: DummyPower()},
            {FeatureName.Play},
        ),
    )

    await facade_dummy.connect()

    # close will return remaining tasks but not run them
    tasks = facade_dummy.close()
    assert not obj.called
    assert not session_manager.session.closed

    # Let remaining tasks run and verify they have finished
    await asyncio.gather(*tasks)
    assert obj.called
    assert session_manager.session.closed


async def test_only_one_device_update(facade_dummy):
    listener = DummyDeviceListener()
    facade_dummy.listener = listener

    facade_dummy.listener.connection_lost(Exception())
    assert listener.lost_calls == 1
    assert listener.closed_calls == 0

    facade_dummy.listener.connection_closed()
    assert listener.lost_calls == 1
    assert listener.closed_calls == 0


async def test_device_update_disconnect_protocols(facade_dummy, register_interface):
    _, dmap_sdg = register_interface(
        FeatureName.Play, DummyFeatures(FeatureName.Play), Protocol.DMAP
    )
    _, mrp_sdg = register_interface(
        FeatureName.Pause, DummyFeatures(FeatureName.Pause), Protocol.MRP
    )

    await facade_dummy.connect()
    facade_dummy.listener.connection_closed()

    assert dmap_sdg.close_called
    assert mrp_sdg.close_called


async def test_close_only_once(facade_dummy, register_interface):
    _, sdg = register_interface(
        FeatureName.Play, DummyFeatures(FeatureName.Play), Protocol.DMAP
    )

    await facade_dummy.connect()

    facade_dummy.close()
    assert sdg.close_calls == 1

    facade_dummy.close()
    assert sdg.close_calls == 1


async def test_close_returns_pending_tasks_from_previous_close(
    facade_dummy, register_interface
):
    _, sdg = register_interface(
        FeatureName.Play, DummyFeatures(FeatureName.Play), Protocol.DMAP
    )

    await facade_dummy.connect()

    task = MagicMock()
    sdg.pending_tasks.add(task)

    facade_dummy.close()
    pending_tasks = facade_dummy.close()
    assert len(pending_tasks) == 1
    assert task in pending_tasks


async def tests_device_info_from_single_protocol(facade_dummy, register_interface):
    _, sdg = register_interface(
        FeatureName.Play, DummyFeatures(FeatureName.Play), Protocol.DMAP
    )
    sdg.device_info.update(
        {
            DeviceInfo.OPERATING_SYSTEM: OperatingSystem.TvOS,
            DeviceInfo.VERSION: "1.0",
        }
    )

    await facade_dummy.connect()

    dev_info = facade_dummy.device_info
    assert dev_info.operating_system == OperatingSystem.TvOS
    assert dev_info.version == "1.0"


async def tests_device_info_from_multiple_protocols(facade_dummy, register_interface):
    _, sdg_dmap = register_interface(
        FeatureName.Play, DummyFeatures(FeatureName.Play), Protocol.DMAP
    )
    _, sdg_mrp = register_interface(
        FeatureName.Pause, DummyFeatures(FeatureName.Pause), Protocol.MRP
    )

    sdg_dmap.device_info.update(
        {
            DeviceInfo.OPERATING_SYSTEM: OperatingSystem.TvOS,
            DeviceInfo.VERSION: "1.0",
        }
    )
    sdg_mrp.device_info.update(
        {
            DeviceInfo.OPERATING_SYSTEM: OperatingSystem.Legacy,
            DeviceInfo.VERSION: "3.0",
            DeviceInfo.BUILD_NUMBER: "ABC",
        }
    )

    await facade_dummy.connect()

    dev_info = facade_dummy.device_info
    assert dev_info.operating_system == OperatingSystem.TvOS
    assert dev_info.version == "1.0"
    assert dev_info.build_number == "ABC"


async def test_stream_play_url_not_available(facade_dummy, register_interface):
    stream, _ = register_interface(FeatureName.Volume, DummyStream(), Protocol.RAOP)

    await facade_dummy.connect()

    with pytest.raises(exceptions.NotSupportedError):
        await facade_dummy.stream.play_url(TEST_URL)


async def test_stream_play_url_available(facade_dummy, register_interface):
    stream, _ = register_interface(FeatureName.PlayUrl, DummyStream(), Protocol.RAOP)

    # play_url requires FeatureName.PlayUrl to be available, so add the feature interface
    register_interface(
        FeatureName.PlayUrl, DummyFeatures(FeatureName.PlayUrl), Protocol.DMAP
    )

    await facade_dummy.connect()

    await facade_dummy.stream.play_url(TEST_URL)

    assert stream.url == TEST_URL
