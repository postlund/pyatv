"""Facade pattern for public interface of pyatv.

This module implements a facade-like pattern by implementing the external interface
of pyatv and relaying calls to methods to the appropriate protocol instance, based on
priority via the relayer module. The purpose is to support partial implementations of
the interface by a protocol, whilst allowing another protocol to implement the rest. If
two protocols implement the same functionality, the protocol with higher "priority" is
picked. See `DEFAULT_PRIORITIES` for priority list.

NB: Typing in this file suffers much from:
https://github.com/python/mypy/issues/5374
"""

import asyncio
import io
import logging
from queue import Queue
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union, cast

from pyatv import const, exceptions, interface
from pyatv.const import FeatureName, FeatureState, InputAction, Protocol, TouchAction
from pyatv.core import CoreStateDispatcher, SetupData, StateMessage, UpdatedState
from pyatv.core.relayer import Relayer
from pyatv.interface import OutputDevice
from pyatv.settings import Settings
from pyatv.support import deprecated, shield
from pyatv.support.collections import dict_merge
from pyatv.support.http import ClientSessionManager

_LOGGER = logging.getLogger(__name__)

DEFAULT_PRIORITIES = [
    Protocol.MRP,
    Protocol.DMAP,
    Protocol.Companion,
    Protocol.AirPlay,
    Protocol.RAOP,
]


class FacadeRemoteControl(Relayer, interface.RemoteControl):
    """Facade implementation for API used to control an Apple TV."""

    def __init__(self):
        """Initialize a new FacadeRemoteControl instance."""
        super().__init__(interface.RemoteControl, DEFAULT_PRIORITIES)

    # pylint: disable=invalid-name
    @shield.guard
    async def up(self, action: InputAction = InputAction.SingleTap) -> None:
        """Press key up."""
        return await self.relay("up")(action=action)

    @shield.guard
    async def down(self, action: InputAction = InputAction.SingleTap) -> None:
        """Press key down."""
        return await self.relay("down")(action=action)

    @shield.guard
    async def left(self, action: InputAction = InputAction.SingleTap) -> None:
        """Press key left."""
        return await self.relay("left")(action=action)

    @shield.guard
    async def right(self, action: InputAction = InputAction.SingleTap) -> None:
        """Press key right."""
        return await self.relay("right")(action=action)

    @shield.guard
    async def play(self) -> None:
        """Press key play."""
        return await self.relay("play")()

    @shield.guard
    async def play_pause(self) -> None:
        """Toggle between play and pause."""
        return await self.relay("play_pause")()

    @shield.guard
    async def pause(self) -> None:
        """Press key play."""
        return await self.relay("pause")()

    @shield.guard
    async def stop(self) -> None:
        """Press key stop."""
        return await self.relay("stop")()

    @shield.guard
    async def next(self) -> None:
        """Press key next."""
        return await self.relay("next")()

    @shield.guard
    async def previous(self) -> None:
        """Press key previous."""
        return await self.relay("previous")()

    @shield.guard
    async def select(self, action: InputAction = InputAction.SingleTap) -> None:
        """Press key select."""
        return await self.relay("select")(action=action)

    @shield.guard
    async def menu(self, action: InputAction = InputAction.SingleTap) -> None:
        """Press key menu."""
        return await self.relay("menu")(action=action)

    @deprecated
    @shield.guard
    async def volume_up(self) -> None:
        """Press key volume up."""
        return await self.relay("volume_up")()

    @deprecated
    @shield.guard
    async def volume_down(self) -> None:
        """Press key volume down."""
        return await self.relay("volume_down")()

    @shield.guard
    async def home(self, action: InputAction = InputAction.SingleTap) -> None:
        """Press key home."""
        return await self.relay("home")(action=action)

    @shield.guard
    async def home_hold(self) -> None:
        """Hold key home."""
        return await self.relay("home_hold")()

    @shield.guard
    async def top_menu(self) -> None:
        """Go to main menu (long press menu)."""
        return await self.relay("top_menu")()

    @deprecated
    @shield.guard
    async def suspend(self) -> None:
        """Suspend the device."""
        return await self.relay("suspend")()

    @deprecated
    @shield.guard
    async def wakeup(self) -> None:
        """Wake up the device."""
        return await self.relay("wakeup")()

    @shield.guard
    async def skip_forward(self, time_interval: float = 0.0) -> None:
        """Skip forward a time interval.

        If time_interval is not positive or not present, a default or app-chosen
        time interval is used, which is typically 10, 15, 30, etc. seconds.
        """
        return await self.relay("skip_forward")(time_interval)

    @shield.guard
    async def skip_backward(self, time_interval: float = 0.0) -> None:
        """Skip backward a time interval.

        If time_interval is not positive or not present, a default or app-chosen
        time interval is used, which is typically 10, 15, 30, etc. seconds.
        """
        return await self.relay("skip_backward")(time_interval)

    @shield.guard
    async def set_position(self, pos: int) -> None:
        """Seek in the current playing media."""
        return await self.relay("set_position")(pos=pos)

    @shield.guard
    async def set_shuffle(self, shuffle_state: const.ShuffleState) -> None:
        """Change shuffle mode to on or off."""
        return await self.relay("set_shuffle")(shuffle_state=shuffle_state)

    @shield.guard
    async def set_repeat(self, repeat_state: const.RepeatState) -> None:
        """Change repeat state."""
        return await self.relay("set_repeat")(repeat_state=repeat_state)

    @shield.guard
    async def channel_up(self) -> None:
        """Select next channel."""
        return await self.relay("channel_up")()

    @shield.guard
    async def channel_down(self) -> None:
        """Select previous channel."""
        return await self.relay("channel_down")()

    @shield.guard
    async def screensaver(self) -> None:
        """Activate screen saver.."""
        return await self.relay("screensaver")()


class FacadeMetadata(Relayer, interface.Metadata):
    """Facade implementation for retrieving metadata from an Apple TV."""

    def __init__(self):
        """Initialize a new FacadeMetadata instance."""
        super().__init__(interface.Metadata, DEFAULT_PRIORITIES)

    @property  # type: ignore
    @shield.guard
    def device_id(self) -> Optional[str]:
        """Return a unique identifier for current device."""
        return self.relay("device_id")

    @shield.guard
    async def artwork(self, width=512, height=None) -> Optional[interface.ArtworkInfo]:
        """Return artwork for what is currently playing (or None).

        The parameters "width" and "height" makes it possible to request artwork of a
        specific size. This is just a request, the device might impose restrictions and
        return artwork of a different size. Set both parameters to None to request
        default size. Set one of them and let the other one be None to keep original
        aspect ratio.
        """
        return await self.relay("artwork")(width=width, height=height)

    @property  # type: ignore
    @shield.guard
    def artwork_id(self) -> str:
        """Return a unique identifier for current artwork."""
        return self.relay("artwork_id")

    @shield.guard
    async def playing(self) -> interface.Playing:
        """Return what is currently playing."""
        return await self.relay("playing")()

    @property  # type: ignore
    @shield.guard
    def app(self) -> Optional[interface.App]:
        """Return information about current app playing something.

        Do note that this property returns which app is currently playing something and
        not which app is currently active. If nothing is playing, the corresponding
        feature will be unavailable.
        """
        return self.relay("app")


class FacadeFeatures(Relayer, interface.Features):
    """Facade implementation for supported feature functionality.

    This class holds a map from feature name to an instance handling that feature name.
    It is optimized for look up speed rather than memory usage.
    """

    def __init__(self, push_updater_relay: Relayer) -> None:
        """Initialize a new FacadeFeatures instance."""
        super().__init__(interface.Features, DEFAULT_PRIORITIES)
        self._push_updater_relay = push_updater_relay
        self._feature_map: Dict[FeatureName, Tuple[Protocol, interface.Features]] = {}

    def add_mapping(self, protocol: Protocol, features: Set[FeatureName]) -> None:
        """Add mapping from protocol to features handled by that protocol."""
        instance = cast(interface.Features, self.get(protocol))
        if instance:
            for feature in features:
                # Add feature to map if missing OR replace if this protocol has higher
                # priority than previous mapping
                if feature not in self._feature_map or self._has_higher_priority(
                    protocol, self._feature_map[feature][0]
                ):
                    self._feature_map[feature] = (protocol, instance)

    @shield.guard
    def get_feature(self, feature_name: FeatureName) -> interface.FeatureInfo:
        """Return current state of a feature."""
        if feature_name == FeatureName.PushUpdates:
            # Multiple protocols can register a push updater implementation, but only
            # one of them will ever be used (i.e. relaying is not done on method
            # level). So if at least one push updater is available, then we can return
            # "Available" here.
            if self._push_updater_relay.count >= 1:
                return interface.FeatureInfo(FeatureState.Available)
        if feature_name in self._feature_map:
            return self._feature_map[feature_name][1].get_feature(feature_name)
        return interface.FeatureInfo(FeatureState.Unsupported)

    @staticmethod
    def _has_higher_priority(first: Protocol, second: Protocol) -> bool:
        return DEFAULT_PRIORITIES.index(first) < DEFAULT_PRIORITIES.index(second)


class FacadePower(Relayer, interface.Power, interface.PowerListener):
    """Facade implementation for retrieving power state from an Apple TV.

    Listener interface: `pyatv.interfaces.PowerListener`
    """

    # Generally favor Companion as it implements power better than MRP
    OVERRIDE_PRIORITIES = [
        Protocol.Companion,
        Protocol.MRP,
        Protocol.DMAP,
        Protocol.AirPlay,
        Protocol.RAOP,
    ]

    def __init__(self, core_dispatcher: CoreStateDispatcher):
        """Initialize a new FacadePower instance."""
        # This is border line, maybe need another structure to support this
        Relayer.__init__(self, interface.Power, self.OVERRIDE_PRIORITIES)
        interface.Power.__init__(self)

    def powerstate_update(
        self, old_state: const.PowerState, new_state: const.PowerState
    ):
        """Device power state was updated.

        Forward power state updates from protocol implementations to actual listener.
        """
        self.listener.powerstate_update(old_state, new_state)

    @property  # type: ignore
    @shield.guard
    def power_state(self) -> const.PowerState:
        """Return device power state."""
        return self.relay("power_state", priority=self.OVERRIDE_PRIORITIES)

    @shield.guard
    async def turn_on(self, await_new_state: bool = False) -> None:
        """Turn device on."""
        await self.relay("turn_on", priority=self.OVERRIDE_PRIORITIES)(
            await_new_state=await_new_state
        )

    @shield.guard
    async def turn_off(self, await_new_state: bool = False) -> None:
        """Turn device off."""
        await self.relay("turn_off", priority=self.OVERRIDE_PRIORITIES)(
            await_new_state=await_new_state
        )


class FacadeStream(Relayer, interface.Stream):  # pylint: disable=too-few-public-methods
    """Facade implementation for stream functionality."""

    def __init__(self, features: interface.Features):
        """Initialize a new FacadeStream instance."""
        super().__init__(interface.Stream, DEFAULT_PRIORITIES)
        self._features = features

    @shield.guard
    def close(self) -> None:
        """Close connection and release allocated resources."""
        self.relay("close")()

    @shield.guard
    async def play_url(self, url: str, **kwargs) -> None:
        """Play media from an URL on the device."""
        if not self._features.in_state(FeatureState.Available, FeatureName.PlayUrl):
            raise exceptions.NotSupportedError("play_url is not supported")

        await self.relay("play_url")(url, **kwargs)

    @shield.guard
    async def stream_file(
        self,
        file: Union[str, io.BufferedIOBase, asyncio.streams.StreamReader],
        /,
        metadata: Optional[interface.MediaMetadata] = None,
        override_missing_metadata: bool = False,
        **kwargs
    ) -> None:
        """Stream local file to device.

        INCUBATING METHOD - MIGHT CHANGE IN THE FUTURE!
        """
        await self.relay("stream_file")(
            file,
            metadata=metadata,
            override_missing_metadata=override_missing_metadata,
            **kwargs,
        )


class FacadeApps(Relayer, interface.Apps):
    """Facade implementation for app handling."""

    def __init__(self):
        """Initialize a new FacadeApps instance."""
        super().__init__(interface.Apps, DEFAULT_PRIORITIES)

    @shield.guard
    async def app_list(self) -> List[interface.App]:
        """Fetch a list of apps that can be launched."""
        return await self.relay("app_list")()

    @shield.guard
    async def launch_app(self, bundle_id_or_url: str) -> None:
        """Launch an app based on bundle ID or URL."""
        await self.relay("launch_app")(bundle_id_or_url)


class FacadeUserAccounts(Relayer, interface.UserAccounts):
    """Facade implementation for account handling."""

    def __init__(self):
        """Initialize a new FacadeUserAccounts instance."""
        super().__init__(interface.UserAccounts, DEFAULT_PRIORITIES)

    @shield.guard
    async def account_list(self) -> List[interface.UserAccount]:
        """Fetch a list of user accounts that can be switched."""
        return await self.relay("account_list")()

    @shield.guard
    async def switch_account(self, account_id: str) -> None:
        """Switch user account by account ID."""
        await self.relay("switch_account")(account_id)


class FacadeAudio(Relayer, interface.Audio):
    """Facade implementation for audio functionality."""

    def __init__(self, core_dispatcher: CoreStateDispatcher):
        """Initialize a new FacadeAudio instance."""
        Relayer.__init__(self, interface.Audio, DEFAULT_PRIORITIES)
        interface.Audio.__init__(self)
        self._volume = 0.0
        self._output_devices: List[interface.OutputDevice] = []
        core_dispatcher.listen_to(UpdatedState.Volume, self._volume_changed)
        core_dispatcher.listen_to(
            UpdatedState.OutputDevices, self._output_devices_changed
        )

    def _volume_changed(self, message: StateMessage) -> None:
        """State of something changed."""
        volume = cast(float, message.value)

        # Compute new state so we can know if we should update or not
        old_level = self._volume
        new_level = self._volume = volume

        # Do not update state in case it didn't change
        if new_level != old_level:
            self.listener.volume_update(old_level, new_level)

    def _output_devices_changed(self, message: StateMessage) -> None:
        """State of output devices changed."""
        output_devices = cast(List[interface.OutputDevice], message.value)

        # Compute new state so we can know if we should update or not
        old_devices = self._output_devices
        new_devices = self._output_devices = output_devices

        # Do not update state in case it didn't change
        if new_devices != old_devices:
            self.listener.outputdevices_update(old_devices, new_devices)

    @shield.guard
    async def volume_up(self) -> None:
        """Press key volume up."""
        return await self.relay("volume_up")()

    @shield.guard
    async def volume_down(self) -> None:
        """Press key volume down."""
        return await self.relay("volume_down")()

    @property  # type: ignore
    @shield.guard
    def volume(self) -> float:
        """Return current volume level."""
        volume = self.relay("volume")
        if 0.0 <= volume <= 100.0:
            return volume
        raise exceptions.ProtocolError(f"volume {volume} is out of range")

    @shield.guard
    async def set_volume(self, level: float) -> None:
        """Change current volume level."""
        if 0.0 <= level <= 100.0:
            await self.relay("set_volume")(level)
        else:
            raise exceptions.ProtocolError(f"volume {level} is out of range")

    @property
    @shield.guard
    def output_devices(self) -> List[OutputDevice]:
        """Return current list of output device IDs."""
        return self.relay("output_devices")

    @shield.guard
    async def add_output_devices(self, *devices: List[str]) -> None:
        """Add output devices."""
        return await self.relay("add_output_devices")(*devices)

    @shield.guard
    async def remove_output_devices(self, *devices: List[str]) -> None:
        """Remove output devices."""
        return await self.relay("remove_output_devices")(*devices)

    @shield.guard
    async def set_output_devices(self, *devices: List[str]) -> None:
        """Set output devices."""
        return await self.relay("set_output_devices")(*devices)


class FacadeKeyboard(Relayer, interface.Keyboard):
    """Facade implementation for keyboard handling."""

    def __init__(self, core_dispatcher: CoreStateDispatcher):
        """Initialize a new FacadeKeyboard instance."""
        Relayer.__init__(self, interface.Keyboard, DEFAULT_PRIORITIES)
        interface.Keyboard.__init__(self)
        self._focus_state: const.KeyboardFocusState = const.KeyboardFocusState.Unknown
        core_dispatcher.listen_to(
            UpdatedState.KeyboardFocus,
            self._focus_state_changed,
            message_filter=lambda message: message.protocol == self.main_protocol,
        )

    def _focus_state_changed(self, message: StateMessage) -> None:
        state = cast(const.KeyboardFocusState, message.value)

        old_state = self._focus_state
        new_state = self._focus_state = state

        if new_state != old_state:
            _LOGGER.debug("Focus state changed from %s to %s", old_state, new_state)
            self.listener.focusstate_update(old_state, new_state)

    @property
    @shield.guard
    def text_focus_state(self) -> const.KeyboardFocusState:
        """Return keyboard focus state."""
        return self.relay("text_focus_state")

    @shield.guard
    async def text_get(self) -> Optional[str]:
        """Get current virtual keyboard text."""
        return await self.relay("text_get")()

    @shield.guard
    async def text_clear(self) -> None:
        """Clear virtual keyboard text."""
        return await self.relay("text_clear")()

    @shield.guard
    async def text_append(self, text: str) -> None:
        """Input text into virtual keyboard."""
        return await self.relay("text_append")(text=text)

    @shield.guard
    async def text_set(self, text: str) -> None:
        """Replace text in virtual keyboard."""
        return await self.relay("text_set")(text=text)


class FacadePushUpdater(
    Relayer[interface.PushUpdater], interface.PushUpdater, interface.PushListener
):
    """Base class for push/async updates from an Apple TV.

    Listener interface: `pyatv.interface.PushListener`
    """

    def __init__(self):
        """Initialize a new PushUpdater."""
        # TODO: python 3.6 seems to have problem with this sometimes
        Relayer.__init__(  # pylint: disable=non-parent-init-called
            self, interface.PushUpdater, DEFAULT_PRIORITIES
        )
        interface.PushUpdater.__init__(self)

    @property  # type: ignore
    @shield.guard
    def active(self) -> bool:
        """Return if push updater has been started."""
        return self.relay("active")

    @shield.guard
    def start(self, initial_delay: int = 0) -> None:
        """Begin to listen to updates.

        If an error occurs, start must be called again.
        """
        for instance in self.instances:
            instance.listener = self
            instance.start(initial_delay)

    @shield.guard
    def stop(self) -> None:
        """No longer forward updates to listener."""
        for instance in self.instances:
            instance.listener = None
            instance.stop()

    def playstatus_update(self, updater, playstatus: interface.Playing) -> None:
        """Inform about changes to what is currently playing."""
        if updater == self.main_instance:
            self.listener.playstatus_update(updater, playstatus)

    def playstatus_error(self, updater, exception: Exception) -> None:
        """Inform about an error when updating play status."""
        if updater == self.main_instance:
            self.listener.playstatus_error(updater, exception)


class FacadeTouchGestures(Relayer, interface.TouchGestures):
    """Facade implementation for touch gestures handling."""

    def __init__(self, core_dispatcher: CoreStateDispatcher):
        """Initialize a new FacadeTouchGestures instance."""
        Relayer.__init__(self, interface.TouchGestures, DEFAULT_PRIORITIES)
        interface.TouchGestures.__init__(self)

    @shield.guard
    async def swipe(
        self, start_x: int, start_y: int, end_x: int, end_y: int, duration_ms: int
    ) -> None:
        """Generate a touch gesture from start to end x,y coordinates."""
        return await self.relay("swipe")(
            start_x=start_x,
            start_y=start_y,
            end_x=end_x,
            end_y=end_y,
            duration_ms=duration_ms,
        )

    @shield.guard
    async def action(self, x: int, y: int, mode: TouchAction) -> None:
        """Generate a touch event to end x,y coordinates."""
        return await self.relay("action")(x=x, y=y, mode=mode)

    @shield.guard
    async def click(self, action: InputAction):
        """Send a touch click.

        :param action: action mode, single tap (0), double tap (1), or hold (2).
        """
        return await self.relay("click")(action=action)


class FacadeAppleTV(interface.AppleTV):
    """Facade implementation of the external interface."""

    def __init__(
        self,
        config: interface.BaseConfig,
        session_manager: ClientSessionManager,
        core_dispatcher: CoreStateDispatcher,
        settings: Settings,
    ):
        """Initialize a new FacadeAppleTV instance."""
        super().__init__(max_calls=1)  # To StateProducer via interface.AppleTV
        self._config = config
        self._session_manager = session_manager
        self._protocols_to_setup: Queue[SetupData] = Queue()
        self._protocol_handlers: Dict[Protocol, SetupData] = {}
        self._push_updates = FacadePushUpdater()
        self._features = FacadeFeatures(self._push_updates)
        self._pending_tasks: Optional[set] = None
        self._device_info = interface.DeviceInfo({})
        self._interfaces = {
            interface.Features: self._features,
            interface.RemoteControl: FacadeRemoteControl(),
            interface.Metadata: FacadeMetadata(),
            interface.Power: FacadePower(core_dispatcher),
            interface.PushUpdater: self._push_updates,
            interface.Stream: FacadeStream(self._features),
            interface.Apps: FacadeApps(),
            interface.UserAccounts: FacadeUserAccounts(),
            interface.Audio: FacadeAudio(core_dispatcher),
            interface.Keyboard: FacadeKeyboard(core_dispatcher),
            interface.TouchGestures: FacadeTouchGestures(core_dispatcher),
        }
        self._settings = settings
        self._shield_everything()

    def _shield_everything(self):
        shield.shield(self)
        for instance in self._interfaces.values():
            shield.shield(instance)

    def _block_everything(self):
        shield.block(self)
        for instance in self._interfaces.values():
            shield.block(instance)

    def add_protocol(self, setup_data: SetupData):
        """Add a new protocol to the relay."""
        # Connecting commits current configuration, thus adding new protocols is not
        # allowed anymore after that
        if self._protocol_handlers:
            raise exceptions.InvalidStateError(
                "cannot add protocol after connect was called"
            )

        _LOGGER.debug("Adding handler for protocol %s", setup_data.protocol)
        self._protocols_to_setup.put(setup_data)

    @shield.guard
    async def connect(self) -> None:
        """Initiate connection to device."""
        # No protocols to setup + no protocols previously set up => no service
        if self._protocols_to_setup.empty() and not self._protocol_handlers:
            raise exceptions.NoServiceError("no service to connect to")

        # Protocols set up already => we have already connected
        if self._protocol_handlers:
            raise exceptions.InvalidStateError("already connected")

        devinfo: Dict[str, Any] = {}

        # Set up protocols, ignoring duplicates
        while not self._protocols_to_setup.empty():
            setup_data = self._protocols_to_setup.get()

            if setup_data.protocol in self._protocol_handlers:
                _LOGGER.debug(
                    "Protocol %s already set up, ignoring", setup_data.protocol
                )
                continue

            _LOGGER.debug("Connecting to protocol: %s", setup_data.protocol)
            if await setup_data.connect():
                _LOGGER.debug("Connected to protocol: %s", setup_data.protocol)
                self._protocol_handlers[setup_data.protocol] = setup_data

                for iface, instance in setup_data.interfaces.items():
                    self._interfaces[iface].register(instance, setup_data.protocol)

                self._features.add_mapping(setup_data.protocol, setup_data.features)
                dict_merge(devinfo, setup_data.device_info())

        self._device_info = interface.DeviceInfo(devinfo)

        # Forward power events in case an interface exists for it
        try:
            power = cast(
                interface.Power, self._interfaces[interface.Power].main_instance
            )
            power.listener = self._interfaces[interface.Power]
        except exceptions.NotSupportedError:
            _LOGGER.debug("Power management not supported by any protocols")

    def close(self) -> Set[asyncio.Task]:
        """Close connection and release allocated resources."""
        # If close was called before, returning pending tasks
        if self._pending_tasks is not None:
            return self._pending_tasks

        # Stop all push updaters otherwise they might continue in the background
        self.push_updater.stop()

        self._pending_tasks = set()
        self._pending_tasks.add(asyncio.create_task(self._session_manager.close()))
        for setup_data in self._protocol_handlers.values():
            self._pending_tasks.update(setup_data.close())

        # Block access to everything in the public interface
        self._block_everything()

        return self._pending_tasks

    def takeover(self, protocol: Protocol, *interfaces: Any) -> Callable[[], None]:
        """Perform takeover of one of one or more protocol.

        Returns a function, that when called, returns the protocols taken over.
        """
        taken_over: List[Relayer] = []

        def _release() -> None:
            _LOGGER.debug("Release %s by %s", interfaces, protocol)
            for relayer in taken_over:
                relayer.release()

        _LOGGER.debug("Takeover %s by %s", interfaces, protocol)

        for iface in interfaces:
            relayer = self._interfaces.get(iface)
            if relayer is None:
                continue

            try:
                relayer.takeover(protocol)
            except exceptions.InvalidStateError:
                _release()
                raise
            taken_over.append(relayer)

        return _release

    @property  # type: ignore
    @shield.guard
    def settings(self) -> Settings:
        """Return device settings used by pyatv."""
        return self._settings

    @property  # type: ignore
    @shield.guard
    def device_info(self) -> interface.DeviceInfo:
        """Return API for device information."""
        return self._device_info

    @property  # type: ignore
    @shield.guard
    def service(self) -> interface.BaseService:
        """Return main service used to connect to the Apple TV."""
        for protocol in DEFAULT_PRIORITIES:
            service = self._config.get_service(protocol)
            if service:
                return service

        raise RuntimeError("no service (bug)")

    @property  # type: ignore
    @shield.guard
    def remote_control(self) -> interface.RemoteControl:
        """Return API for controlling the Apple TV."""
        return cast(interface.RemoteControl, self._interfaces[interface.RemoteControl])

    @property  # type: ignore
    @shield.guard
    def metadata(self) -> interface.Metadata:
        """Return API for retrieving metadata from the Apple TV."""
        return cast(interface.Metadata, self._interfaces[interface.Metadata])

    @property  # type: ignore
    @shield.guard
    def push_updater(self) -> interface.PushUpdater:
        """Return API for handling push update from the Apple TV."""
        return cast(interface.PushUpdater, self._interfaces[interface.PushUpdater])

    @property  # type: ignore
    @shield.guard
    def stream(self) -> interface.Stream:
        """Return API for streaming media."""
        return cast(interface.Stream, self._interfaces[interface.Stream])

    @property  # type: ignore
    @shield.guard
    def power(self) -> interface.Power:
        """Return API for power management."""
        return cast(interface.Power, self._interfaces[interface.Power])

    @property  # type: ignore
    @shield.guard
    def features(self) -> interface.Features:
        """Return features interface."""
        return cast(interface.Features, self._interfaces[interface.Features])

    @property  # type: ignore
    @shield.guard
    def apps(self) -> interface.Apps:
        """Return apps interface."""
        return cast(interface.Apps, self._interfaces[interface.Apps])

    @property  # type: ignore
    @shield.guard
    def user_accounts(self) -> interface.UserAccounts:
        """Return user accounts interface."""
        return cast(interface.UserAccounts, self._interfaces[interface.UserAccounts])

    @property  # type: ignore
    @shield.guard
    def audio(self) -> interface.Audio:
        """Return audio interface."""
        return cast(interface.Audio, self._interfaces[interface.Audio])

    @property  # type: ignore
    @shield.guard
    def keyboard(self) -> interface.Keyboard:
        """Return keyboard interface."""
        return cast(interface.Keyboard, self._interfaces[interface.Keyboard])

    @property  # type: ignore
    @shield.guard
    def touch(self) -> interface.TouchGestures:
        """Return touch gestures interface."""
        return cast(interface.TouchGestures, self._interfaces[interface.TouchGestures])

    def state_was_updated(self) -> None:
        """Call when state was updated.

        One of the protocol called a method in DeviceListener so everything should
        be torn down.
        """
        self.close()
