"""PoC code for Companion protocol."""

import asyncio
from enum import Enum
import logging
from typing import Any, Awaitable, Callable, Dict, List, Optional, Set, Tuple, cast

from pyatv import conf, exceptions
from pyatv.companion.connection import CompanionConnection, FrameType
from pyatv.companion.protocol import CompanionProtocol
from pyatv.conf import AppleTV
from pyatv.const import FeatureName, FeatureState, Protocol
from pyatv.interface import App, Apps, FeatureInfo, Features, Power, StateProducer
from pyatv.support.hap_srp import SRPAuthHandler
from pyatv.support.net import ClientSessionManager
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


async def _connect(loop, config: AppleTV) -> CompanionProtocol:
    """Connect to the device."""
    service = config.get_service(Protocol.Companion)
    if service is None:
        raise exceptions.NoCredentialsError("No Companion credentials loaded")

    _LOGGER.debug("Connect to Companion from API")
    connection = CompanionConnection(loop, str(config.address), service.port)
    protocol = CompanionProtocol(connection, SRPAuthHandler(), service)
    await protocol.start()
    return protocol


# TODO: Maybe move to separate file?
class CompanionAPI:
    """Implementation of Companion API.

    This class implements a simple one-shot request based API. It will connect and
    disconnect for every request. Mainly as a workaround for not knowing how to keep
    a connection open at all time (as the remote device disconnects after a while).
    """

    def __init__(self, config: AppleTV, loop: asyncio.AbstractEventLoop):
        """Initialize a new CompanionAPI instance."""
        self.config = config
        self.loop = loop

    async def _send_command(
        self, identifier: str, content: Dict[str, object]
    ) -> Dict[str, object]:
        """Send a command to the device and return response."""
        protocol = None
        try:
            protocol = await _connect(self.loop, self.config)

            resp = await protocol.exchange_opack(
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
        finally:
            if protocol:
                protocol.stop()

        return resp

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
