"""PoC code for Companion protocol."""

import asyncio
import logging
from typing import Dict, List, cast

from pyatv import exceptions
from pyatv.companion.connection import CompanionConnection, FrameType
from pyatv.companion.protocol import CompanionProtocol
from pyatv.conf import AppleTV
from pyatv.const import Protocol
from pyatv.interface import App, Apps
from pyatv.support.hap_srp import SRPAuthHandler

_LOGGER = logging.getLogger(__name__)


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


class CompanionApps(Apps):
    """Implementation of API for app handling."""

    def __init__(self, api: CompanionAPI):
        """Initialize a new instance of CompanionApps."""
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
