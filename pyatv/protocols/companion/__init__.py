"""PoC code for Companion protocol."""

import asyncio
from enum import Enum
import logging
from random import randint
from typing import Any, Dict, Generator, List, Mapping, Optional, Set, cast

from pyatv import exceptions
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
from pyatv.protocols.companion.connection import (
    CompanionConnection,
    CompanionConnectionListener,
    FrameType,
)
from pyatv.protocols.companion.pairing import CompanionPairingHandler
from pyatv.protocols.companion.protocol import CompanionProtocol
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

SUPPORTED_FEATURES = set(
    [
        FeatureName.AppList,
        FeatureName.LaunchApp,
        FeatureName.TurnOn,
        FeatureName.TurnOff,
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
)

# pylint: disable=invalid-name


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


# pylint: enable=invalid-name


# TODO: Maybe move to separate file?
class CompanionAPI(CompanionConnectionListener):
    """Implementation of Companion API."""

    def __init__(self, config: BaseConfig, loop: asyncio.AbstractEventLoop):
        """Initialize a new CompanionAPI instance."""
        self.config = config
        self.loop = loop
        self._connection: Optional[CompanionConnection] = None
        self._protocol: Optional[CompanionProtocol] = None
        self.sid: int = 0

    async def disconnect(self):
        """Disconnect from companion device."""
        # TODO: Should send _sessionStop
        if self._protocol:
            self._protocol.stop()

    async def _connect(self):
        if self._protocol:
            return

        service = self.config.get_service(Protocol.Companion)
        if service is None:
            raise exceptions.NoCredentialsError("No Companion credentials loaded")

        _LOGGER.debug("Connect to Companion from API")
        connection = CompanionConnection(
            self.loop, str(self.config.address), service.port, self
        )

        protocol = CompanionProtocol(connection, SRPAuthHandler(), service)
        await protocol.start()

        self._connection = connection
        self._protocol = protocol

        await self._session_start()

    def disconnected(self) -> None:
        """Call back when disconnected from companion device."""
        _LOGGER.debug("API got disconnected from Companion device")
        self._connection = None
        self._protocol = None

    async def _send_command(
        self, identifier: str, content: Dict[str, object]
    ) -> Dict[str, object]:
        """Send a command to the device and return response."""
        await self._connect()
        if self._protocol is None:
            raise RuntimeError("not connected to companion")

        try:
            resp = await self._protocol.exchange_opack(
                FrameType.E_OPACK,
                {
                    "_i": identifier,
                    "_x": 12356,  # Dummy XID, not sure what to use
                    "_t": "2",  # Request
                    "_c": content,
                },
            )
        except exceptions.ProtocolError:
            raise
        except Exception as ex:
            raise exceptions.ProtocolError(f"Command {identifier} failed") from ex
        else:
            return resp

    async def _session_start(self):
        local_sid = randint(0, 2 ** 32 - 1)
        resp = await self._send_command(
            "_sessionStart", {"_srvT": "com.apple.tvremoteservices", "_sid": local_sid}
        )

        remote_sid = resp["_c"]["_sid"]
        self.sid = (remote_sid << 32) | local_sid
        _LOGGER.debug("Started session with SID 0x%X", self.sid)

    async def launch_app(self, bundle_identifier: str) -> None:
        """Launch an app on the remote device."""
        await self._send_command("_launchApp", {"_bundleID": bundle_identifier})

    async def app_list(self) -> Dict[str, object]:
        """Return list of launchable apps on remote device."""
        return await self._send_command("FetchLaunchableApplicationsEvent", {})

    async def hid_command(self, down: bool, command: HidCommand) -> None:
        """Send a HID command."""
        await self._send_command(
            "_hidC", {"_hBtS": 1 if down else 2, "_hidC": command.value}
        )


class CompanionFeatures(Features):
    """Implementation of supported feature functionality."""

    def __init__(self, service: BaseService) -> None:
        """Initialize a new CompanionFeatures instance."""
        super().__init__()
        self.service = service

    def get_feature(self, feature_name: FeatureName) -> FeatureInfo:
        """Return current state of a feature."""
        # Credentials are needed, so cannot be available without them
        if self.service.credentials is not None:
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

    async def _press_button(
        self, command: HidCommand, action: InputAction = InputAction.SingleTap
    ) -> None:
        if action != InputAction.SingleTap:
            raise NotImplementedError(f"{action} not supported for {command} (yet)")
        await self.api.hid_command(False, command)


class CompanionAudio(Audio):
    """Implementation of audio API."""

    def __init__(self, api: CompanionAPI) -> None:
        """Initialize a new CompanionAudio instance."""
        self.api = api

    async def volume_up(self) -> None:
        """Increase volume by one step."""
        await self.api.hid_command(False, HidCommand.VolumeUp)

    async def volume_down(self) -> None:
        """Decrease volume by one step."""
        await self.api.hid_command(False, HidCommand.VolumeDown)


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
        return None

    api = CompanionAPI(config, loop)

    interfaces = {
        Apps: CompanionApps(api),
        Features: CompanionFeatures(service),
        Power: CompanionPower(api),
        RemoteControl: CompanionRemoteControl(api),
        Audio: CompanionAudio(api),
    }

    async def _connect() -> bool:
        return True

    def _close() -> Set[asyncio.Task]:
        return set()

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
