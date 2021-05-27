"""PoC code for Companion protocol."""

import asyncio
from enum import Enum
import logging
from random import randint
from typing import Any, Awaitable, Callable, Dict, List, Optional, Set, Tuple, cast

from pyatv import conf, exceptions
from pyatv.companion.connection import (
    CompanionConnection,
    CompanionConnectionListener,
    FrameType,
)
from pyatv.companion.protocol import CompanionProtocol
from pyatv.conf import AppleTV
from pyatv.const import FeatureName, FeatureState, Protocol
from pyatv.interface import App, Apps, FeatureInfo, Features, Power, StateProducer
from pyatv.support.hap_srp import SRPAuthHandler
from pyatv.support.http import ClientSessionManager
from pyatv.support.relayer import Relayer

_LOGGER = logging.getLogger(__name__)


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

    def __init__(self, config: AppleTV, loop: asyncio.AbstractEventLoop):
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
        except Exception as ex:
            raise exceptions.ProtocolError(f"Command {identifier} failed") from ex
        else:
            # Check if an error was present and throw exception if that's the case
            if "_em" in resp:
                raise exceptions.ProtocolError(
                    f"Command {identifier} failed: {resp['_em']}"
                )

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

    async def sleep(self):
        """Put device to sleep."""
        await self._hid_command(False, HidCommand.Sleep)

    async def wake(self):
        """Wake up sleeping device."""
        await self._hid_command(False, HidCommand.Wake)

    async def _hid_command(self, down: bool, command: HidCommand) -> None:
        await self._send_command(
            "_hidC", {"_hBtS": 1 if down else 2, "_hidC": command.value}
        )


class CompanionFeatures(Features):
    """Implementation of supported feature functionality."""

    def __init__(self, service: conf.CompanionService) -> None:
        """Initialize a new CompanionFeatures instance."""
        super().__init__()
        self.service = service

    def get_feature(self, feature_name: FeatureName) -> FeatureInfo:
        """Return current state of a feature."""
        # Credentials are needed, so cannot be available without them
        if self.service.credentials is not None:
            # Just assume these are available for now if the protocol is configured,
            # we don't have any way to verify it anyways.
            if feature_name in [
                FeatureName.AppList,
                FeatureName.LaunchApp,
                FeatureName.TurnOn,
                FeatureName.TurnOff,
            ]:
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
        await self.api.wake()

    async def turn_off(self, await_new_state: bool = False) -> None:
        """Turn device off."""
        # TODO: add support for this
        if await_new_state:
            raise NotImplementedError("not supported by Companion yet")
        await self.api.sleep()


def setup(
    loop: asyncio.AbstractEventLoop,
    config: conf.AppleTV,
    interfaces: Dict[Any, Relayer],
    device_listener: StateProducer,
    session_manager: ClientSessionManager,
) -> Optional[
    Tuple[Callable[[], Awaitable[None]], Callable[[], None], Set[FeatureName]]
]:
    """Set up a new Companion service."""
    service = config.get_service(Protocol.Companion)
    assert service is not None

    # Companion doesn't work without credentials, so don't setup if none exists
    if not service.credentials:
        return None

    api = CompanionAPI(config, loop)

    interfaces[Apps].register(CompanionApps(api), Protocol.Companion)
    interfaces[Features].register(
        CompanionFeatures(cast(conf.CompanionService, service)), Protocol.Companion
    )
    interfaces[Power].register(CompanionPower(api), Protocol.Companion)

    async def _connect() -> None:
        pass

    def _close() -> None:
        pass

    return (
        _connect,
        _close,
        set(
            [
                FeatureName.AppList,
                FeatureName.LaunchApp,
                FeatureName.TurnOn,
                FeatureName.TurnOff,
            ]
        ),
    )
