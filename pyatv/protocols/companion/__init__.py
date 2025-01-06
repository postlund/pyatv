"""PoC code for Companion protocol."""

import asyncio
from enum import IntFlag
import logging
from typing import Any, Dict, Generator, List, Mapping, Optional, Set, cast

from pyatv import exceptions
from pyatv.const import (
    DeviceModel,
    FeatureName,
    FeatureState,
    InputAction,
    KeyboardFocusState,
    PairingRequirement,
    PowerState,
    Protocol,
    TouchAction,
)
from pyatv.core import Core, MutableService, SetupData, UpdatedState, mdns
from pyatv.core.scan import (
    ScanHandlerDeviceInfoName,
    ScanHandlerReturn,
    device_info_name_from_unique_short_name,
)
from pyatv.helpers import get_unique_id
from pyatv.interface import (
    App,
    Apps,
    Audio,
    BaseService,
    DeviceInfo,
    FeatureInfo,
    Features,
    Keyboard,
    PairingHandler,
    Power,
    RemoteControl,
    TouchGestures,
    UserAccount,
    UserAccounts,
)
from pyatv.protocols.companion.api import (
    CompanionAPI,
    HidCommand,
    MediaControlCommand,
    SystemStatus,
)
from pyatv.protocols.companion.pairing import CompanionPairingHandler
from pyatv.support.device_info import lookup_model

_LOGGER = logging.getLogger(__name__)

# Observed values of rpfl (zeroconf):
# 0x62792 -> All on the same network (Unsupported/Mandatory)
# 0x627B6 -> Only devices in same home (Disabled)
# 0xB67A2 -> Same as above
# Mask = 0x62792 & ~0xB67A2 & ~0x627B6 & ~0xB67A2 = 0x20
PAIRING_DISABLED_MASK = 0x04

# Pairing with PIN seems to be supported according to this pattern
# (again, observed from values of rpfl):
#
# Not pairable:
# 0010 0000 0000 0000 0000 = 0x20000 (Mac Mini, MacBook)
# 0110 0010 0111 1011 0010 = 0x627B2 (HomePod, HomePod mini)
# 0110 0010 0111 1001 0010 = 0x62792 (HomePod mini)
# 0011 0000 0000 0000 0000 = 0x30000 (iPad)
#
# Pairable:
# 0011 0110 0111 1010 0010 = 0x367A2 (Apple TV 4K)
# 0011 0110 0111 1000 0010 = 0x36782 (Apple TV 4K)
# ===
# 0000 0100 0000 0000 0000 = 0x04000
#
# So masking 0x40000 should tell if pairing is supported or not (in a way
# that pyatv supports).
PAIRING_WITH_PIN_SUPPORTED_MASK = 0x4000

# As seen in the TV Remote App
_DEFAULT_SKIP_TIME = 10

# pylint: disable=invalid-name


class MediaControlFlags(IntFlag):
    """Media control flags used to indicate available controls."""

    NoControls = 0x0000
    Play = 0x0001
    Pause = 0x0002
    NextTrack = 0x0004
    PreviousTrack = 0x0008
    FastForward = 0x0010
    Rewind = 0x0020
    # ? = 0x0040
    # ? = 0x0080
    Volume = 0x0100
    SkipForward = 0x0200
    SkipBackward = 0x0400


# pylint: enable=invalid-name

MEDIA_CONTROL_MAP = {
    FeatureName.Play: MediaControlFlags.Play,
    FeatureName.Pause: MediaControlFlags.Pause,
    FeatureName.Next: MediaControlFlags.NextTrack,
    FeatureName.Previous: MediaControlFlags.PreviousTrack,
    FeatureName.Volume: MediaControlFlags.Volume,
    FeatureName.SetVolume: MediaControlFlags.Volume,
    FeatureName.SkipForward: MediaControlFlags.SkipForward,
    FeatureName.SkipBackward: MediaControlFlags.SkipBackward,
}

SUPPORTED_FEATURES = set(
    [
        # App interface
        FeatureName.AppList,
        FeatureName.LaunchApp,
        # User account interface
        FeatureName.AccountList,
        FeatureName.SwitchAccount,
        # Power interface
        FeatureName.PowerState,
        FeatureName.TurnOn,
        FeatureName.TurnOff,
        # Remote control (navigation, i.e. HID)
        FeatureName.Up,
        FeatureName.Down,
        FeatureName.Left,
        FeatureName.Right,
        FeatureName.Select,
        FeatureName.Menu,
        FeatureName.Home,
        FeatureName.VolumeUp,
        FeatureName.VolumeDown,
        FeatureName.PlayPause,
        FeatureName.ChannelUp,
        FeatureName.ChannelDown,
        FeatureName.Screensaver,
        # Keyboard interface
        FeatureName.TextFocusState,
        FeatureName.TextGet,
        FeatureName.TextClear,
        FeatureName.TextAppend,
        FeatureName.TextSet,
        FeatureName.Swipe,
        FeatureName.Action,
        FeatureName.Click,
    ]
    # Remote control (playback, i.e. Media Control)
    + list(MEDIA_CONTROL_MAP.keys())
)


class CompanionApps(Apps):
    """Implementation of API for app handling."""

    def __init__(self, api: CompanionAPI):
        """Initialize a new instance of CompanionApps."""
        super().__init__()
        self.api = api

    async def app_list(self) -> List[App]:
        """Fetch a list of apps that can be launched."""
        app_list = await self.api.app_list()
        if "_c" not in app_list:
            raise exceptions.ProtocolError("missing content in response")

        content = cast(dict, app_list["_c"])
        return [App(name, bundle_id) for bundle_id, name in content.items()]

    async def launch_app(self, bundle_id_or_url: str) -> None:
        """Launch an app based on bundle ID or URL."""
        await self.api.launch_app(bundle_id_or_url)


class CompanionUserAccounts(UserAccounts):
    """Implementation of API for account handling."""

    def __init__(self, api: CompanionAPI):
        """Initialize a new instance of CompanionUserAccounts."""
        super().__init__()
        self.api = api

    async def account_list(self) -> List[UserAccount]:
        """Fetch a list of user accounts that can be switched."""
        account_list = await self.api.account_list()
        if "_c" not in account_list:
            raise exceptions.ProtocolError("missing content in response")

        content = cast(dict, account_list["_c"])
        return [UserAccount(name, account_id) for account_id, name in content.items()]

    async def switch_account(self, account_id: str) -> None:
        """Switch user account by account ID."""
        await self.api.switch_account(account_id)


class CompanionPower(Power):
    """Implementation of power management API."""

    def __init__(self, api: CompanionAPI):
        """Initialize a new instance of CompanionPower."""
        super().__init__()
        self.api: CompanionAPI = api
        self.loop = asyncio.get_event_loop()
        self._power_state: PowerState = PowerState.Unknown

    @property
    def supports_power_updates(self) -> bool:
        """Return if power updates are supported or not."""
        return self._power_state is not PowerState.Unknown

    async def initialize(self) -> None:
        """Initialize Power module."""
        try:
            system_status = await self.api.fetch_attention_state()

            self._power_state = CompanionPower._system_status_to_power_state(
                system_status
            )

            self.api.listen_to("SystemStatus", self._handle_system_status_update)
            await self.api.subscribe_event("SystemStatus")

            self.api.listen_to("TVSystemStatus", self._handle_system_status_update)
            await self.api.subscribe_event("TVSystemStatus")

            _LOGGER.debug("Initial power state is %s", self.power_state)
        except Exception as ex:
            _LOGGER.exception(
                "Could not fetch SystemStatus, power_state will not work (%s)", ex
            )

    @property
    def power_state(self) -> PowerState:
        """Return device power state."""
        return self._power_state

    async def _handle_system_status_update(self, data: Mapping[str, Any]) -> None:
        try:
            old_state = self.power_state
            self._power_state = CompanionPower._system_status_to_power_state(
                SystemStatus(int(data["state"]))
            )
            self._update_power_state(old_state, self._power_state)
        except Exception:
            logging.exception("Got invalid SystemStatus: %s", data)

    @staticmethod
    def _system_status_to_power_state(system_status: SystemStatus) -> PowerState:
        if system_status == SystemStatus.Asleep:
            return PowerState.Off
        if system_status in [
            SystemStatus.Screensaver,
            SystemStatus.Awake,
            SystemStatus.Idle,
        ]:
            return PowerState.On
        return PowerState.Unknown

    def _update_power_state(self, old_state: PowerState, new_state: PowerState) -> None:
        if new_state != old_state:
            _LOGGER.debug("Power state changed from %s to %s", old_state, new_state)
            self.loop.call_soon(self.listener.powerstate_update, old_state, new_state)

    async def turn_on(self, await_new_state: bool = False) -> None:
        """Turn device on."""
        # TODO: add support for this
        if await_new_state:
            raise NotImplementedError("not supported by Companion yet")
        await self.api.hid_command(False, HidCommand.Wake)

    async def turn_off(self, await_new_state: bool = False) -> None:
        """Turn device off."""
        # TODO: add support for this
        if await_new_state:
            raise NotImplementedError("not supported by Companion yet")
        await self.api.hid_command(False, HidCommand.Sleep)


class CompanionRemoteControl(RemoteControl):
    """Implementation of remote control API."""

    def __init__(self, api: CompanionAPI) -> None:
        """Initialize a new CompanionRemoteControl."""
        self.api = api

    # pylint: disable=invalid-name
    async def up(self, action: InputAction = InputAction.SingleTap) -> None:
        """Press key up."""
        await self._press_button(HidCommand.Up, action)

    async def down(self, action: InputAction = InputAction.SingleTap) -> None:
        """Press key down."""
        await self._press_button(HidCommand.Down, action)

    async def left(self, action: InputAction = InputAction.SingleTap) -> None:
        """Press key left."""
        await self._press_button(HidCommand.Left, action)

    async def right(self, action: InputAction = InputAction.SingleTap) -> None:
        """Press key right."""
        await self._press_button(HidCommand.Right, action)

    async def select(self, action: InputAction = InputAction.SingleTap) -> None:
        """Press key select."""
        await self._press_button(HidCommand.Select, action)

    async def menu(self, action: InputAction = InputAction.SingleTap) -> None:
        """Press key menu."""
        await self._press_button(HidCommand.Menu, action)

    async def home(self, action: InputAction = InputAction.SingleTap) -> None:
        """Press key home."""
        await self._press_button(HidCommand.Home, action)

    async def volume_up(self) -> None:
        """Press key volume up."""
        await self._press_button(HidCommand.VolumeUp)

    async def volume_down(self) -> None:
        """Press key volume down."""
        await self._press_button(HidCommand.VolumeDown)

    async def play_pause(self) -> None:
        """Toggle between play and pause."""
        await self._press_button(HidCommand.PlayPause)

    async def play(self) -> None:
        """Press key play."""
        await self.api.mediacontrol_command(MediaControlCommand.Play)

    async def pause(self) -> None:
        """Press key play."""
        await self.api.mediacontrol_command(MediaControlCommand.Pause)

    async def next(self) -> None:
        """Press key next."""
        await self.api.mediacontrol_command(MediaControlCommand.NextTrack)

    async def previous(self) -> None:
        """Press key previous."""
        await self.api.mediacontrol_command(MediaControlCommand.PreviousTrack)

    async def skip_forward(self, time_interval: float = 0.0) -> None:
        """Skip forward a time interval."""
        await self.api.mediacontrol_command(
            MediaControlCommand.SkipBy,
            {
                "_skpS": float(
                    time_interval if time_interval > 0 else _DEFAULT_SKIP_TIME
                )
            },
        )

    async def skip_backward(self, time_interval: float = 0.0) -> None:
        """Skip forward a time interval."""
        # float cast: opack fails with negative integers
        await self.api.mediacontrol_command(
            MediaControlCommand.SkipBy,
            {
                "_skpS": float(
                    -time_interval if time_interval > 0 else -_DEFAULT_SKIP_TIME
                )
            },
        )

    async def channel_up(self) -> None:
        """Select next channel."""
        await self._press_button(HidCommand.ChannelIncrement)

    async def channel_down(self) -> None:
        """Select previous channel."""
        await self._press_button(HidCommand.ChannelDecrement)

    async def screensaver(self) -> None:
        """Activate screen saver."""
        await self._press_button(HidCommand.Screensaver)

    async def _press_button(
        self,
        command: HidCommand,
        action: InputAction = InputAction.SingleTap,
        delay: float = 1,
    ) -> None:
        if action == InputAction.SingleTap:
            await self.api.hid_command(True, command)
            await self.api.hid_command(False, command)

        elif action == InputAction.Hold:
            await self.api.hid_command(True, command)
            await asyncio.sleep(delay)
            await self.api.hid_command(False, command)

        elif action == InputAction.DoubleTap:
            # First press
            await self.api.hid_command(True, command)
            await self.api.hid_command(False, command)
            # Second press
            await self.api.hid_command(True, command)
            await self.api.hid_command(False, command)
        else:
            raise exceptions.NotSupportedError(f"unsupported input action: {action}")


class CompanionAudio(Audio):
    """Implementation of audio API."""

    def __init__(self, api: CompanionAPI, core: Core) -> None:
        """Initialize a new CompanionAudio instance."""
        self.api = api
        self.api.listen_to("_iMC", self._handle_control_flag_update)
        self.core = core
        self._volume_event: asyncio.Event = asyncio.Event()
        self._volume = 0.0

    async def _handle_control_flag_update(self, data: Mapping[str, Any]) -> None:
        if data["_mcF"] & MediaControlFlags.Volume:
            _LOGGER.debug("Volume control changed, updating volume")

            resp = await self.api.mediacontrol_command(MediaControlCommand.GetVolume)
            self._volume = resp["_c"]["_vol"] * 100.0
            _LOGGER.debug("Volume changed to %f", self._volume)
            self._volume_event.set()
        else:
            # No volume control means we know nothing about the volume
            self._volume = 0.0

        self.core.state_dispatcher.dispatch(UpdatedState.Volume, self.volume)

    @property
    def volume(self) -> float:
        """Return current volume level.

        Range is in percent, i.e. [0.0-100.0].
        """
        return self._volume

    async def set_volume(self, level: float) -> None:
        """Change current volume level.

        Range is in percent, i.e. [0.0-100.0].
        """
        self._volume_event.clear()
        await self.api.mediacontrol_command(
            MediaControlCommand.SetVolume, {"_vol": level / 100.0}
        )

        await asyncio.wait_for(self._volume_event.wait(), timeout=5.0)

    async def volume_up(self) -> None:
        """Increase volume by one step."""
        self._volume_event.clear()
        await self.api.hid_command(True, HidCommand.VolumeUp)
        await self.api.hid_command(False, HidCommand.VolumeUp)
        await asyncio.wait_for(self._volume_event.wait(), timeout=5.0)

    async def volume_down(self) -> None:
        """Decrease volume by one step."""
        self._volume_event.clear()
        await self.api.hid_command(True, HidCommand.VolumeDown)
        await self.api.hid_command(False, HidCommand.VolumeDown)
        await asyncio.wait_for(self._volume_event.wait(), timeout=5.0)


class CompanionKeyboard(Keyboard):
    """Implementation of API for keyboard handling."""

    def __init__(self, api: CompanionAPI, core: Core):
        """Initialize a new instance of CompanionKeyboard."""
        super().__init__()
        self.api = api
        # _tiStarted will not be sent if session is started while already focused
        self.api.listen_to("_tiStarted", self._handle_text_input)
        self.api.listen_to("_tiStopped", self._handle_text_input)
        # _tiStart is actually a command that we forward the response of,
        self.api.listen_to("_tiStart", self._handle_text_input)
        self.core = core
        self._focus_state: KeyboardFocusState = KeyboardFocusState.Unknown

    async def _handle_text_input(self, data: Mapping[str, Any]) -> None:
        state = (
            KeyboardFocusState.Focused
            if "_tiD" in data
            else KeyboardFocusState.Unfocused
        )
        self._focus_state = state
        self.core.state_dispatcher.dispatch(UpdatedState.KeyboardFocus, state)

    @property
    def text_focus_state(self) -> KeyboardFocusState:
        """Return keyboard focus state."""
        return self._focus_state

    async def text_get(self) -> Optional[str]:
        """Get current virtual keyboard text."""
        return await self.api.text_input_command("", clear_previous_input=False)

    async def text_clear(self) -> None:
        """Clear virtual keyboard text."""
        await self.api.text_input_command("", clear_previous_input=True)

    async def text_append(self, text: str) -> None:
        """Input text into virtual keyboard."""
        await self.api.text_input_command(text, clear_previous_input=False)

    async def text_set(self, text: str) -> None:
        """Replace text in virtual keyboard."""
        await self.api.text_input_command(text, clear_previous_input=True)


class CompanionTouchGestures(TouchGestures):
    """Implementation of touch gesture API."""

    def __init__(self, api: CompanionAPI) -> None:
        """Initialize a new CompanionTouchGeatures."""
        self.api = api

    # pylint: disable=invalid-name
    async def swipe(
        self, start_x: int, start_y: int, end_x: int, end_y: int, duration_ms: int
    ) -> None:
        """Generate a touch swipe.

         From start to end x,y coordinates (in range [0,1000])
         in a given time (in milliseconds).

        :param start_x: Start x coordinate
        :param start_y: Start y coordinate
        :param end_x: End x coordinate
        :param end_y: Endi x coordinate
        :param duration_ms: Time in milliseconds to reach the end coordinates
        """
        await self.api.swipe(start_x, start_y, end_x, end_y, duration_ms)

    async def action(self, x: int, y: int, mode: TouchAction):
        """Generate a touch event to x,y coordinates (in range [0,1000]).

        :param x: x coordinate
        :param y: y coordinate
        :param mode: touch mode (1: press, 3: hold, 4: release)
        """
        await self.api.action(x, y, mode)

    async def click(self, action: InputAction):
        """Send a touch click.

        :param action: action mode single tap (0), double tap (1), or hold (2)
        """
        await self.api.click(action)


class CompanionFeatures(Features):
    """Implementation of supported feature functionality."""

    def __init__(self, api: CompanionAPI, power: CompanionPower) -> None:
        """Initialize a new CompanionFeatures instance."""
        super().__init__()
        api.listen_to("_iMC", self._handle_control_flag_update)
        self._control_flags = MediaControlFlags.NoControls
        self._power = power

    async def _handle_control_flag_update(self, data: Mapping[str, Any]) -> None:
        self._control_flags = MediaControlFlags(data["_mcF"])
        _LOGGER.debug("Updated media control flags to %s", self._control_flags)

    def get_feature(self, feature_name: FeatureName) -> FeatureInfo:
        """Return current state of a feature."""
        if feature_name in MEDIA_CONTROL_MAP:
            is_available = MEDIA_CONTROL_MAP[feature_name] & self._control_flags
            return FeatureInfo(
                FeatureState.Available if is_available else FeatureState.Unavailable
            )

        if feature_name == FeatureName.PowerState:
            return FeatureInfo(
                FeatureState.Available
                if self._power.supports_power_updates
                else FeatureState.Unsupported
            )

        # Just assume these are available for now if the protocol is configured,
        # we don't have any way to verify it anyways.
        if feature_name in SUPPORTED_FEATURES:
            return FeatureInfo(FeatureState.Available)

        return FeatureInfo(FeatureState.Unavailable)


def companion_service_handler(
    mdns_service: mdns.Service, response: mdns.Response
) -> Optional[ScanHandlerReturn]:
    """Parse and return a new Companion service."""
    service = MutableService(
        get_unique_id(mdns_service.type, mdns_service.name, mdns_service.properties),
        Protocol.Companion,
        mdns_service.port,
        mdns_service.properties,
    )
    return mdns_service.name, service


def scan() -> Mapping[str, ScanHandlerDeviceInfoName]:
    """Return handlers used for scanning."""
    return {
        "_companion-link._tcp.local": (
            companion_service_handler,
            device_info_name_from_unique_short_name,
        )
    }


def device_info(service_type: str, properties: Mapping[str, Any]) -> Dict[str, Any]:
    """Return device information from zeroconf properties."""
    devinfo: Dict[str, Any] = {}
    if "rpmd" in properties:
        model = lookup_model(properties["rpmd"])
        devinfo[DeviceInfo.RAW_MODEL] = properties["rpmd"]
        if model != DeviceModel.Unknown:
            devinfo[DeviceInfo.MODEL] = model
    return devinfo


async def service_info(
    service: MutableService,
    devinfo: DeviceInfo,
    services: Mapping[Protocol, BaseService],
) -> None:
    """Update service with additional information."""
    flags = int(service.properties.get("rpfl", "0x0"), 16)
    if flags & PAIRING_DISABLED_MASK:
        service.pairing = PairingRequirement.Disabled
    elif flags & PAIRING_WITH_PIN_SUPPORTED_MASK:
        service.pairing = PairingRequirement.Mandatory
    else:
        service.pairing = PairingRequirement.Unsupported


def setup(core: Core) -> Generator[SetupData, None, None]:
    """Set up a new Companion service."""
    # Companion doesn't work without credentials, so don't setup if none exists
    if not core.service.credentials:
        _LOGGER.debug("Not adding Companion as credentials are missing")
        return None

    api = CompanionAPI(core)
    power = CompanionPower(api)

    interfaces = {
        Apps: CompanionApps(api),
        UserAccounts: CompanionUserAccounts(api),
        Features: CompanionFeatures(api, power),
        Power: power,
        RemoteControl: CompanionRemoteControl(api),
        Audio: CompanionAudio(api, core),
        Keyboard: CompanionKeyboard(api, core),
        TouchGestures: CompanionTouchGestures(api),
    }

    async def _connect() -> bool:
        await api.connect()
        await power.initialize()
        return True

    def _close() -> Set[asyncio.Task]:
        return set([asyncio.ensure_future(api.disconnect())])

    def _device_info() -> Dict[str, Any]:
        return device_info(list(scan().keys())[0], core.service.properties)

    yield SetupData(
        Protocol.Companion,
        _connect,
        _close,
        _device_info,
        interfaces,
        SUPPORTED_FEATURES,
    )


def pair(core: Core, **kwargs) -> PairingHandler:
    """Return pairing handler for protocol."""
    return CompanionPairingHandler(core, **kwargs)
