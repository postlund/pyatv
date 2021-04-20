"""PoC code for Companion protocol."""

import logging
import asyncio
from typing import Optional, List, Dict, cast

from pyatv.conf import AppleTV
from pyatv.const import Protocol
from pyatv.interface import Apps, App

from pyatv.companion.connection import CompanionConnection, FrameType
from pyatv.companion.protocol import CompanionProtocol
from pyatv.support.hap_srp import SRPAuthHandler

_LOGGER = logging.getLogger(__name__)


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
        self.service = self.config.get_service(Protocol.Companion)
        self._protocol: Optional[CompanionProtocol] = None

    def close(self):
        """Close and free resources."""
        if self._protocol:
            self._protocol.stop()
            self._protocol = None

    async def _connect(self):
        """Connect to the device."""
        _LOGGER.debug("Connect to Companion from API")
        connection = CompanionConnection(
            self.loop, self.config.address, self.service.port
        )
        self._protocol = CompanionProtocol(connection, SRPAuthHandler(), self.service)
        await self._protocol.start()

    async def _send_command(
        self, identifier: str, content: Dict[str, object]
    ) -> Dict[str, object]:
        """Launch an app n the remote device."""
        try:
            if self._protocol is None:
                await self._connect()

            if self._protocol is None:
                raise Exception("failed to connect")  # TODO: Better exception

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
            # TODO: Better exception
            raise Exception(f"command {identifier} failed") from ex
        else:
            # Check if an error was present and throw exception if that's the case
            if "_em" in resp:
                # TODO: Better exception
                raise Exception(f"command {identifier} failed: {resp['_em']}")
        finally:
            if self._protocol:
                self._protocol.stop()
                self._protocol = None

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
            raise Exception("missing content in response")  # TODO: Better exception

        content = cast(dict, app_list["_c"])
        return [App(name, bundle_id) for bundle_id, name in content.items()]

    async def launch_app(self, bundle_id: str) -> None:
        """Launch an app based on bundle ID."""
        await self.api.launch_app(bundle_id)
