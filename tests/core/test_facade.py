"""Unit tests for pyatv.core.facade."""

from abc import ABC
import asyncio
import inspect
from ipaddress import IPv4Address
import logging
import math
from typing import Any, Dict, List, Set
from unittest.mock import MagicMock

import pytest
import pytest_asyncio

from pyatv import const, exceptions
from pyatv.conf import AppleTV as AppleTVConf
from pyatv.const import (
    DeviceState,
    FeatureName,
    KeyboardFocusState,
    MediaType,
    OperatingSystem,
    PowerState,
    Protocol,
)
from pyatv.core import AbstractPushUpdater, SetupData, UpdatedState
from pyatv.core.facade import FacadeAppleTV, SetupData
from pyatv.interface import (
    AppleTV,
    Apps,
    Audio,
    AudioListener,
    DeviceInfo,
    DeviceListener,
    FeatureInfo,
    Features,
    FeatureState,
    Keyboard,
    KeyboardListener,
    Metadata,
    OutputDevice,
    Playing,
    Power,
    PushListener,
    PushUpdater,
    RemoteControl,
    Stream,
)
from pyatv.settings import Settings

from tests.shared_helpers import SavingPowerListener
from tests.utils import until

_LOGGER = logging.getLogger(__name__)

TEST_URL = "http://test"

pytestmark = pytest.mark.asyncio


@pytest.fixture(name="facade_dummy")
def facade_dummy_fixture(session_manager, core_dispatcher):
    conf = AppleTVConf(IPv4Address("127.0.0.1"), "Test")
    settings = Settings()
    facade = FacadeAppleTV(conf, session_manager, core_dispatcher, settings)
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


class DummyPower(Power):
    def __init__(self) -> None:
        self.current_state = PowerState.Off
        self.turn_on_called = False
        self.turn_off_called = False

    @property
    def power_state(self):
        return self.current_state

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
        self._volume = level


class DummyKeyboard(Keyboard):
    def __init__(self, focus_state: KeyboardFocusState) -> None:
        self._focus_state = focus_state

    @property
    def focus_state(self) -> KeyboardFocusState:
        return self._focus_state


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


class DummyPushUpdater(AbstractPushUpdater):
    def __init__(self, state_dispatcher):
        super().__init__(state_dispatcher)
        self._active = False

    @property
    def active(self) -> bool:
        return self._active

    def start(self, initial_delay: int = 0) -> None:
        self._active = True

    def stop(self) -> None:
        self._active = False


class SavingPushListener(PushListener):
    def __init__(self):
        self.last_update = None
        self.no_of_updates = 0

    def playstatus_update(self, updater, playstatus: Playing) -> None:
        self.last_update = playstatus
        self.no_of_updates += 1

    def playstatus_error(self, updater, exception: Exception) -> None:
        pass


class SavingAudioListener(AudioListener):
    def __init__(self):
        self.last_update = None
        self.all_updates = []

    def volume_update(self, old_level: float, new_level: float):
        """Device volume was updated."""
        self.last_update = new_level
        self.all_updates.append(new_level)

    def outputdevices_update(
        self, old_devices: List[OutputDevice], new_devices: List[OutputDevice]
    ):
        """Output devices were updated."""
        self.last_update = new_devices
        self.all_updates.append(new_devices)


class SavingKeyboardListener(KeyboardListener):
    def __init__(self):
        self.last_update = None
        self.all_updates = []

    def focusstate_update(
        self, old_state: const.KeyboardFocusState, new_state: const.KeyboardFocusState
    ):
        self.last_update = new_state
        self.all_updates.append(new_state)


@pytest.fixture(name="register_interface")
def register_interface_fixture(facade_dummy):
    def _register_func(feature: FeatureName, instance, protocol: Protocol):
        # Find the first derived interface from pyatv.interface module
        interface = next(
            iface
            for iface in inspect.getmro(type(instance))
            if iface.__module__ == "pyatv.interface"
        )
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


async def test_features_push_updates(
    facade_dummy, register_interface, mrp_state_dispatcher
):
    feat = facade_dummy.features

    assert feat.get_feature(FeatureName.PushUpdates).state == FeatureState.Unsupported

    register_interface(
        FeatureName.PushUpdates,
        DummyPushUpdater(mrp_state_dispatcher),
        Protocol.MRP,
    )

    await facade_dummy.connect()
    assert feat.get_feature(FeatureName.PushUpdates).state == FeatureState.Available


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
    assert len(pending_tasks) == 2
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


async def test_takeover_and_release(facade_dummy, register_interface):
    register_interface(FeatureName.Volume, DummyAudio(100.0), Protocol.RAOP)
    register_interface(FeatureName.Volume, DummyAudio(0.0), Protocol.MRP)

    await facade_dummy.connect()
    audio = facade_dummy.audio

    # MRP has priority, so should return that volume
    assert math.isclose(audio.volume, 0.0)

    takeover_release = facade_dummy.takeover(Protocol.RAOP, Audio)

    # RAOP has performed takeover, so should return volume from there
    assert math.isclose(audio.volume, 100.0)

    takeover_release()

    # Back to MRP again
    assert math.isclose(audio.volume, 0.0)


def register_basic_interfaces(reg_interface, protocol: Protocol) -> None:
    _, sdg = reg_interface(
        FeatureName.PlayUrl, DummyFeatures(FeatureName.PlayUrl), protocol
    )
    sdg.interfaces[Audio] = DummyAudio(0.0)
    sdg.interfaces[Keyboard] = DummyKeyboard(KeyboardFocusState.Unfocused)
    sdg.interfaces[Stream] = DummyStream()
    return sdg


async def test_takeover_failure_restores(facade_dummy, register_interface):
    register_basic_interfaces(register_interface, Protocol.RAOP)
    register_basic_interfaces(register_interface, Protocol.DMAP)
    sdg_mrp = register_basic_interfaces(register_interface, Protocol.MRP)

    await facade_dummy.connect()
    audio = facade_dummy.audio

    # RAOP takes over Audio
    facade_dummy.takeover(Protocol.RAOP, Audio)

    with pytest.raises(exceptions.InvalidStateError):
        # DMAP tries to take over Stream and Audio, but fails since Audio has
        # already been taken over by RAOP (so entire takeover is rolled back)
        facade_dummy.takeover(Protocol.DMAP, Stream, Audio)

    # Play something via Stream, which uses regular priority
    await facade_dummy.stream.play_url("test")

    # MRP has highest priority, so it should be used
    assert sdg_mrp.interfaces[Stream].url == "test"


async def test_takeover_push_updates(
    facade_dummy, register_interface, mrp_state_dispatcher, dmap_state_dispatcher
):
    listener = SavingPushListener()

    dmap_pusher = DummyPushUpdater(dmap_state_dispatcher)
    mrp_pusher = DummyPushUpdater(mrp_state_dispatcher)

    async def _perform_update(expected_updates, expected_protocol):
        dmap_pusher.post_update(
            Playing(MediaType.Music, DeviceState.Idle, title=f"dmap_{expected_updates}")
        )
        mrp_pusher.post_update(
            Playing(MediaType.Music, DeviceState.Idle, title=f"mrp_{expected_updates}")
        )

        await until(lambda: listener.no_of_updates == expected_updates)
        assert listener.last_update.title == f"{expected_protocol}_{expected_updates}"

    register_interface(FeatureName.PushUpdates, dmap_pusher, Protocol.DMAP)
    register_interface(FeatureName.PushUpdates, mrp_pusher, Protocol.MRP)

    await facade_dummy.connect()
    push_updater = facade_dummy.push_updater
    push_updater.listener = listener
    push_updater.start()

    # Trigger push updates from both protocols without any takeover. In this case only
    # priority is used, so update from MRP should be delivered.
    await _perform_update(1, "mrp")

    takeover_release = facade_dummy.takeover(Protocol.DMAP, PushUpdater)

    # After takeover, push update from RAOP should be delivered instead
    await _perform_update(2, "dmap")

    takeover_release()

    # Back to MRP again
    await _perform_update(3, "mrp")


# All push updaters must be started and stopped in parallel, otherwise updates will
# not be pushed when performing a takeover (as the protocol taken over was never
# started)
async def test_start_stop_all_push_updaters(
    facade_dummy, register_interface, mrp_state_dispatcher, dmap_state_dispatcher
):
    dmap_pusher = DummyPushUpdater(dmap_state_dispatcher)
    mrp_pusher = DummyPushUpdater(mrp_state_dispatcher)

    register_interface(FeatureName.PushUpdates, dmap_pusher, Protocol.DMAP)
    register_interface(FeatureName.PushUpdates, mrp_pusher, Protocol.MRP)

    await facade_dummy.connect()
    push_updater = facade_dummy.push_updater

    assert not dmap_pusher.active
    assert not mrp_pusher.active

    push_updater.start()

    assert dmap_pusher.active
    assert mrp_pusher.active

    push_updater.stop()

    assert not dmap_pusher.active
    assert not mrp_pusher.active


async def test_push_updaters_stop_on_close(
    facade_dummy, register_interface, mrp_state_dispatcher, dmap_state_dispatcher
):
    dmap_pusher = DummyPushUpdater(dmap_state_dispatcher)
    mrp_pusher = DummyPushUpdater(mrp_state_dispatcher)

    register_interface(FeatureName.PushUpdates, dmap_pusher, Protocol.DMAP)
    register_interface(FeatureName.PushUpdates, mrp_pusher, Protocol.MRP)

    await facade_dummy.connect()
    push_updater = facade_dummy.push_updater
    push_updater.start()
    facade_dummy.close()

    assert not dmap_pusher.active
    assert not mrp_pusher.active


# POWER RELATED TESTS


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


@pytest_asyncio.fixture(name="power_instance")
async def power_instance_fixture():
    yield DummyPower()


@pytest_asyncio.fixture(name="power_setup")
async def power_setup_fixture(facade_dummy, register_interface, power_instance):
    listener = SavingPowerListener()

    register_interface(FeatureName.PowerState, power_instance, Protocol.MRP)

    await facade_dummy.connect()
    facade_dummy.power.listener = listener

    yield facade_dummy.power


async def dispatch_device_state(mrp_state_dispatcher, state, protocol=Protocol.MRP):
    event = asyncio.Event()

    # Add a listener last in the last and make it set an asyncio.Event. That way we
    # can synchronize and know that all other listeners have been called.
    mrp_state_dispatcher.listen_to(UpdatedState.Playing, lambda message: event.set())
    mrp_state_dispatcher.dispatch(
        UpdatedState.Playing, Playing(MediaType.Unknown, state)
    )

    await event.wait()


async def test_power_state_defaults_to_derived_power_state_from_on(
    mrp_state_dispatcher, power_setup, power_instance
):
    power_instance.current_state = PowerState.On

    # Trigger something to play (but keep power state off) changes it to On
    await dispatch_device_state(mrp_state_dispatcher, DeviceState.Playing)
    assert power_setup.listener.last_update is None

    # Trigger back to idle shall give power state On as derived state is On
    await dispatch_device_state(mrp_state_dispatcher, DeviceState.Idle)
    assert power_setup.power_state == PowerState.On
    assert power_setup.listener.last_update is None


async def test_power_play_state_no_listener_duplicates(
    mrp_state_dispatcher, power_setup
):
    assert power_setup.power_state == PowerState.Off

    # Dispatch "On" and then trigger a listener update with "On", which should not
    # yield any additional update
    await dispatch_device_state(mrp_state_dispatcher, DeviceState.Playing)
    power_setup.powerstate_update(PowerState.Off, PowerState.On)

    assert len(power_setup.listener.all_updates) == 1
    assert power_setup.listener.last_update == PowerState.On


async def test_power_no_updates_without_power_instance(
    mrp_state_dispatcher, facade_dummy, register_interface
):
    listener = SavingPowerListener()

    # Some kind of interface is needed to connect (arbitrary but not Power)
    register_interface(FeatureName.Play, DummyFeatures(FeatureName.Play), Protocol.DMAP)

    await facade_dummy.connect()
    facade_dummy.power.listener = listener

    # Defensive to make sure we have no instance
    with pytest.raises(exceptions.NotSupportedError):
        facade_dummy.power.power_state

    await dispatch_device_state(mrp_state_dispatcher, DeviceState.Playing)
    assert listener.last_update is None


# AUDIO RELATED TESTS


@pytest_asyncio.fixture(name="audio_setup")
async def audio_setup_fixture(facade_dummy, register_interface):
    listener = SavingAudioListener()

    register_basic_interfaces(register_interface, Protocol.MRP)

    await facade_dummy.connect()
    facade_dummy.audio.listener = listener

    yield facade_dummy.audio


async def dispatch_volume_update(mrp_state_dispatcher, level, protocol=Protocol.MRP):
    event = asyncio.Event()

    # Add a listener last in the last and make it set an asyncio.Event. That way we
    # can synchronize and know that all other listeners have been called.
    mrp_state_dispatcher.listen_to(UpdatedState.Volume, lambda message: event.set())
    mrp_state_dispatcher.dispatch(UpdatedState.Volume, level)

    await event.wait()


async def dispatch_output_devices_update(
    mrp_state_dispatcher, devices, protocol=Protocol.MRP
):
    event = asyncio.Event()

    # Add a listener last in the last and make it set an asyncio.Event. That way we
    # can synchronize and know that all other listeners have been called.
    mrp_state_dispatcher.listen_to(
        UpdatedState.OutputDevices, lambda message: event.set()
    )
    mrp_state_dispatcher.dispatch(UpdatedState.OutputDevices, devices)

    await event.wait()


async def test_audio_listener_volume_updates(mrp_state_dispatcher, audio_setup):
    await dispatch_volume_update(mrp_state_dispatcher, 10.0)
    assert audio_setup.listener.last_update == 10.0
    await dispatch_volume_update(mrp_state_dispatcher, 20.0)
    assert audio_setup.listener.last_update == 20.0


async def test_audio_no_listener_volume_duplicates(mrp_state_dispatcher, audio_setup):
    await dispatch_volume_update(mrp_state_dispatcher, 10.0)
    await dispatch_volume_update(mrp_state_dispatcher, 10.0)
    assert len(audio_setup.listener.all_updates) == 1
    assert audio_setup.listener.last_update == 10.0


async def test_audio_listener_output_devices_updates(mrp_state_dispatcher, audio_setup):
    await dispatch_output_devices_update(
        mrp_state_dispatcher,
        [OutputDevice("Apple TV", "AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE")],
    )
    assert audio_setup.listener.last_update == [
        OutputDevice("Apple TV", "AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE")
    ]
    await dispatch_output_devices_update(
        mrp_state_dispatcher,
        [
            OutputDevice("Apple TV", "AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE"),
            OutputDevice("HomePod", "FFFFFFFF-GGGG-HHHH-IIII-JJJJJJJJJJJJ"),
        ],
    )
    assert audio_setup.listener.last_update == [
        OutputDevice("Apple TV", "AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE"),
        OutputDevice("HomePod", "FFFFFFFF-GGGG-HHHH-IIII-JJJJJJJJJJJJ"),
    ]


async def test_audio_no_listener_output_devices_duplicates(
    mrp_state_dispatcher, audio_setup
):
    await dispatch_output_devices_update(
        mrp_state_dispatcher,
        [OutputDevice("Apple TV", "AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE")],
    )
    await dispatch_output_devices_update(
        mrp_state_dispatcher,
        [OutputDevice("Apple TV", "AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE")],
    )
    assert len(audio_setup.listener.all_updates) == 1
    assert audio_setup.listener.last_update == [
        OutputDevice("Apple TV", "AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE")
    ]


# KEYBOARD RELATED TESTS


@pytest_asyncio.fixture(name="keyboard_setup")
async def keyboard_setup_fixture(facade_dummy, register_interface):
    listener = SavingKeyboardListener()

    register_basic_interfaces(register_interface, Protocol.Companion)

    await facade_dummy.connect()
    facade_dummy.keyboard.listener = listener

    yield facade_dummy.keyboard


async def dispatch_focus_state_update(
    companion_state_dispatcher, state, protocol=Protocol.Companion
):
    event = asyncio.Event()

    # Add a listener last in the last and make it set an asyncio.Event. That way we
    # can synchronize and know that all other listeners have been called.
    companion_state_dispatcher.listen_to(
        UpdatedState.KeyboardFocus, lambda message: event.set()
    )
    companion_state_dispatcher.dispatch(UpdatedState.KeyboardFocus, state)

    await event.wait()


async def test_keyboard_listener_updates(companion_state_dispatcher, keyboard_setup):
    await dispatch_focus_state_update(
        companion_state_dispatcher, KeyboardFocusState.Focused
    )
    assert keyboard_setup.listener.last_update == KeyboardFocusState.Focused
    await dispatch_focus_state_update(
        companion_state_dispatcher, KeyboardFocusState.Unfocused
    )
    assert keyboard_setup.listener.last_update == KeyboardFocusState.Unfocused


async def test_keyboard_no_listener_duplicates(
    companion_state_dispatcher, keyboard_setup
):
    await dispatch_focus_state_update(
        companion_state_dispatcher, KeyboardFocusState.Focused
    )
    await dispatch_focus_state_update(
        companion_state_dispatcher, KeyboardFocusState.Focused
    )
    assert len(keyboard_setup.listener.all_updates) == 1
    assert keyboard_setup.listener.last_update == KeyboardFocusState.Focused


# GUARD CALLS AFTER CLOSE


# Retrieve method names of all methods (and properties) in an interface but exclude
# members inherited from super classes.
def get_interface_methods(iface, base_methods=None):
    if base_methods is None:
        base_methods = set(dir(iface))

    for base in iface.__bases__:
        # Remove objects that comes from current super class
        base_methods.difference_update(set(dir(base)) & base_methods)
        get_interface_methods(base, base_methods)
    return set(method for method in base_methods if not method.startswith("_"))


def assert_interface_guarded(obj, iface, exclude=None):
    # All methods and properties in the base object should be properly guarded
    for method_name in get_interface_methods(iface) - (exclude or set()):
        with pytest.raises(exceptions.BlockedStateError):
            try:
                method = getattr(obj, method_name)
                if inspect.ismethod(method):
                    method()
            except exceptions.BlockedStateError:
                _LOGGER.debug(
                    "Method %s in %s is properly guarded", method_name, iface.__name__
                )
                raise
            else:
                raise Exception(
                    f"method {method_name} in {iface.__name__} is not guarded"
                )


async def test_base_methods_guarded_after_close(facade_dummy, register_interface):
    register_interface(FeatureName.Play, DummyFeatures(FeatureName.Play), Protocol.DMAP)
    await facade_dummy.connect()
    facade_dummy.close()
    assert_interface_guarded(facade_dummy, AppleTV, exclude={"close"})


@pytest.mark.parametrize(
    "iface,member,exclude",
    [
        (RemoteControl, "remote_control", {}),
        (Metadata, "metadata", {}),
        (PushUpdater, "push_updater", {}),
        (Stream, "stream", {}),
        (Power, "power", {}),
        # in_states is not abstract but uses get_features, will which will raise
        (Features, "features", {"in_state"}),
        (Apps, "apps", {}),
        (Audio, "audio", {}),
    ],
)
async def test_interface_methods_guarded_after_close(
    facade_dummy, register_interface, iface, member, exclude
):
    register_interface(FeatureName.Play, DummyFeatures(FeatureName.Play), Protocol.DMAP)
    await facade_dummy.connect()

    # Store reference to interface prior to closing to simulate something like this:
    # atv = await connect(...)
    # rc = atv.remote_control
    # atv.close()
    # await rc.left()
    instance = getattr(facade_dummy, member)
    facade_dummy.close()

    assert_interface_guarded(instance, iface, exclude=exclude)
