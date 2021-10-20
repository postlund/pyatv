"""PoC code for Companion protocol."""

import asyncio
from enum import Enum, IntFlag
import logging
from random import randint
from typing import Any, Dict, Generator, List, Mapping, Optional, Set, cast

from pyatv import exceptions
from pyatv.auth.hap_pairing import parse_credentials
from pyatv.auth.hap_srp import SRPAuthHandler
from pyatv.const import (
    DeviceModel,
    FeatureName,
    FeatureState,
    InputAction,
    PairingRequirement,
    Protocol,
)
from pyatv.core import MutableService, SetupData, TakeoverMethod, mdns
from pyatv.core.protocol import MessageDispatcher
from pyatv.core.scan import ScanHandler, ScanHandlerReturn
from pyatv.interface import (
    App,
    Apps,
    Audio,
    BaseConfig,
    BaseService,
    DeviceInfo,
    FeatureInfo,
    Features,
    PairingHandler,
    Power,
    RemoteControl,
)
from pyatv.protocols.companion.connection import CompanionConnection, FrameType
from pyatv.protocols.companion.pairing import CompanionPairingHandler
from pyatv.protocols.companion.protocol import (
    CompanionProtocol,
    CompanionProtocolListener,
    MessageType,
)
from pyatv.support.device_info import lookup_model
from pyatv.support.http import ClientSessionManager
from pyatv.support.state_producer import StateProducer

_LOGGER = logging.getLogger(__name__)

# Observed values of rpfl (zeroconf):
# 0x62792 -> All on the same network (Unsupported/Mandatory)
# 0x627B6 -> Only devices in same home (Disabled)
# Mask = 0x62792 & ~0x627B6 = 0x24
PAIRING_DISABLED_MASK = 0x24

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


class HidCommand(Enum):
    """HID command constants."""

    Up = 1
    Down = 2
    Left = 3
    Right = 4
    Menu = 5
    Select = 6
    Home = 7
    VolumeUp = 8
    VolumeDown = 9
    Siri = 10
    Screensaver = 11
    Sleep = 12
    Wake = 13
    PlayPause = 14
    ChannelIncrement = 15
    ChannelDecrement = 16
    Guide = 17
    PageUp = 18
    PageDown = 19


class MediaControlCommand(Enum):
    """Media Control command constants."""

    Play = 1
    Pause = 2
    NextTrack = 3
    PreviousTrack = 4
    GetVolume = 5
    SetVolume = 6
    SkipBy = 7
    FastForwardBegin = 8
    FastForwardEnd = 9
    RewindBegin = 10
    RewindEnd = 11
    GetCaptionSettings = 12
    SetCaptionSettings = 13


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
        # Power interface
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
    ]
    # Remote control (playback, i.e. Media Control)
    + list(MEDIA_CONTROL_MAP.keys())
)


# TODO: Maybe move to separate file?
class CompanionAPI(
    MessageDispatcher[str, Mapping[str, Any]], CompanionProtocolListener
):
    """Implementation of Companion API."""

    def __init__(
        self,
        config: BaseConfig,
        service: BaseService,
        device_listener: StateProducer,
        loop: asyncio.AbstractEventLoop,
    ):
        """Initialize a new CompanionAPI instance."""
        super().__init__()
        self.config = config
        self.service = service
        self.loop = loop
        self._device_listener = device_listener
        self._connection: Optional[CompanionConnection] = None
        self._protocol: Optional[CompanionProtocol] = None
        self.sid: int = 0

    async def disconnect(self):
        """Disconnect from companion device."""
        if self._protocol is None:
            return

        try:
            # Sometimes unsubscribe fails for an unknown reason, but we are no
            # going to bother with that and just swallow the error.
            await self.unsubscribe_event("_iMC")
            await self._session_stop()
        except Exception as ex:
            _LOGGER.debug("Ignoring error during disconnect: %s", ex)
        finally:
            self._protocol.stop()
            self._protocol = None

    def event_received(self, event_name: str, data: Dict[str, Any]) -> None:
        """Event was received."""
        _LOGGER.debug("Got event %s from device: %s", event_name, data)
        self.dispatch(event_name, data)

    async def connect(self):
        """Connect to remote host."""
        if self._protocol:
            return

        _LOGGER.debug("Connect to Companion from API")
        self._connection = CompanionConnection(
            self.loop,
            str(self.config.address),
            self.service.port,
            self._device_listener,
        )
        self._protocol = CompanionProtocol(
            self._connection, SRPAuthHandler(), self.service
        )
        self._protocol.listener = self
        await self._protocol.start()

        await self.system_info()
        await self._session_start()
        await self.subscribe_event("_iMC")

    async def _send_command(
        self,
        identifier: str,
        content: Dict[str, object],
        message_type: MessageType = MessageType.Request,
    ) -> Mapping[str, Any]:
        """Send a command to the device and return response."""
        await self.connect()
        if self._protocol is None:
            raise RuntimeError("not connected to companion")

        try:
            resp = await self._protocol.exchange_opack(
                FrameType.E_OPACK,
                {
                    "_i": identifier,
                    "_x": 1234,  # Dummy XID, not sure what to use
                    "_t": message_type.value,
                    "_c": content,
                },
            )
        except exceptions.ProtocolError:
            raise
        except Exception as ex:
            raise exceptions.ProtocolError(f"Command {identifier} failed") from ex
        else:
            return resp

    async def system_info(self):
        """Send system information to device."""
        _LOGGER.debug("Sending system information")
        creds = parse_credentials(self.service.credentials)

        # Bunch of semi-random values here...
        await self._send_command(
            "_systemInfo",
            {
                "_bf": 0,
                "_cf": 512,
                "_clFl": 128,
                "_i": "cafecafecafe",  # TODO: Figure out what to put here
                "_idsID": creds.client_id,
                "_pubID": "aa:bb:cc:dd:ee:ff",
                "_sf": 256,  # Status flags?
                "_sv": "170.18",  # Software Version (I guess?)
                "model": "iPhone14,3",
                "name": "pyatv",
            },
        )

    async def _session_start(self) -> None:
        local_sid = randint(0, 2 ** 32 - 1)
        resp = await self._send_command(
            "_sessionStart", {"_srvT": "com.apple.tvremoteservices", "_sid": local_sid}
        )

        content = resp.get("_c")
        if content is None:
            raise exceptions.ProtocolError("missing content")

        remote_sid = cast(Mapping[str, Any], resp["_c"])["_sid"]
        self.sid = (remote_sid << 32) | local_sid
        _LOGGER.debug("Started session with SID 0x%X", self.sid)

    async def _session_stop(self) -> None:
        await self._send_command(
            "_sessionStop", {"_srvT": "com.apple.tvremoteservices", "_sid": self.sid}
        )
        _LOGGER.debug("Stopped session with SID 0x%X", self.sid)

    async def _send_event(self, identifier: str, content: Mapping[str, Any]) -> None:
        """Subscribe to updates to an event."""
        await self.connect()
        if self._protocol is None:
            raise RuntimeError("not connected to companion")

        try:
            self._protocol.send_opack(
                FrameType.E_OPACK,
                {
                    "_i": identifier,
                    "_x": 1234,  # Dummy XID, not sure what to use
                    "_t": MessageType.Event.value,
                    "_c": content,
                },
            )
        except exceptions.ProtocolError:
            raise
        except Exception as ex:
            raise exceptions.ProtocolError("Send event failed") from ex

    async def subscribe_event(self, event: str) -> None:
        """Subscribe to updates to an event."""
        await self._send_event("_interest", {"_regEvents": [event]})

    async def unsubscribe_event(self, event: str) -> None:
        """Subscribe to updates to an event."""
        await self._send_event("_interest", {"_deregEvents": [event]})

    async def launch_app(self, bundle_identifier: str) -> None:
        """Launch an app on the remote device."""
        await self._send_command("_launchApp", {"_bundleID": bundle_identifier})

    async def app_list(self) -> Mapping[str, Any]:
        """Return list of launchable apps on remote device."""
        return await self._send_command("FetchLaunchableApplicationsEvent", {})

    async def hid_command(self, down: bool, command: HidCommand) -> None:
        """Send a HID command."""
        await self._send_command(
            "_hidC", {"_hBtS": 1 if down else 2, "_hidC": command.value}
        )

    async def mediacontrol_command(
        self, command: MediaControlCommand, args: Optional[Mapping[str, Any]] = None
    ) -> Mapping[str, Any]:
        """Send a HID command."""
        return await self._send_command("_mcc", {"_mcc": command.value, **(args or {})})


class CompanionFeatures(Features):
    """Implementation of supported feature functionality."""

    def __init__(self, api: CompanionAPI) -> None:
        """Initialize a new CompanionFeatures instance."""
        super().__init__()
        api.listen_to("_iMC", self._handle_control_flag_update)
        self._control_flags = MediaControlFlags.NoControls

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

        # Just assume these are available for now if the protocol is configured,
        # we don't have any way to verify it anyways.
        if feature_name in SUPPORTED_FEATURES:
            return FeatureInfo(FeatureState.Available)

        return FeatureInfo(FeatureState.Unavailable)


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

    async def launch_app(self, bundle_id: str) -> None:
        """Launch an app based on bundle ID."""
        await self.api.launch_app(bundle_id)


class CompanionPower(Power):
    """Implementation of power management API."""

    def __init__(self, api: CompanionAPI):
        """Initialize a new instance of CompanionPower."""
        super().__init__()
        self.api = api

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

    async def _press_button(
        self, command: HidCommand, action: InputAction = InputAction.SingleTap
    ) -> None:
        if action != InputAction.SingleTap:
            raise NotImplementedError(f"{action} not supported for {command} (yet)")
        await self.api.hid_command(True, command)
        await self.api.hid_command(False, command)


class CompanionAudio(Audio):
    """Implementation of audio API."""

    def __init__(self, api: CompanionAPI) -> None:
        """Initialize a new CompanionAudio instance."""
        self.api = api
        self.api.listen_to("_iMC", self._handle_control_flag_update)
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


def companion_service_handler(
    mdns_service: mdns.Service, response: mdns.Response
) -> Optional[ScanHandlerReturn]:
    """Parse and return a new Companion service."""
    service = MutableService(
        None,
        Protocol.Companion,
        mdns_service.port,
        mdns_service.properties,
    )
    return mdns_service.name, service


def scan() -> Mapping[str, ScanHandler]:
    """Return handlers used for scanning."""
    return {"_companion-link._tcp.local": companion_service_handler}


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


def setup(
    loop: asyncio.AbstractEventLoop,
    config: BaseConfig,
    service: BaseService,
    device_listener: StateProducer,
    session_manager: ClientSessionManager,
    takeover: TakeoverMethod,
) -> Generator[SetupData, None, None]:
    """Set up a new Companion service."""
    # Companion doesn't work without credentials, so don't setup if none exists
    if not service.credentials:
        _LOGGER.debug("Not adding Companion as credentials are missing")
        return None

    api = CompanionAPI(config, service, device_listener, loop)

    interfaces = {
        Apps: CompanionApps(api),
        Features: CompanionFeatures(api),
        Power: CompanionPower(api),
        RemoteControl: CompanionRemoteControl(api),
        Audio: CompanionAudio(api),
    }

    async def _connect() -> bool:
        await api.connect()
        return True

    def _close() -> Set[asyncio.Task]:
        return set([asyncio.ensure_future(api.disconnect())])

    def _device_info() -> Dict[str, Any]:
        return device_info(list(scan().keys())[0], service.properties)

    yield SetupData(
        Protocol.Companion,
        _connect,
        _close,
        _device_info,
        interfaces,
        SUPPORTED_FEATURES,
    )


def pair(
    config: BaseConfig,
    service: BaseService,
    session_manager: ClientSessionManager,
    loop: asyncio.AbstractEventLoop,
    **kwargs
) -> PairingHandler:
    """Return pairing handler for protocol."""
    return CompanionPairingHandler(config, service, session_manager, loop, **kwargs)
