"""PoC code for Companion protocol."""

import logging
import asyncio
from typing import Optional

from pyatv.const import Protocol
from pyatv.conf import AppleTV

from pyatv.companion.connection import CompanionConnection, FrameType
from pyatv.companion.protocol import CompanionProtocol
from pyatv.support.hap_srp import SRPAuthHandler

_LOGGER = logging.getLogger(__name__)


class CompanionAPI:
    """Implementation of companion API."""

    def __init__(self, config: AppleTV, loop: asyncio.AbstractEventLoop):
        """Initialize a new CompanionAPI instance."""
        self.config = config
        self.loop = loop
        self.service = self.config.get_service(Protocol.Companion)
        self.protocol: Optional[CompanionProtocol] = None

    def close(self):
        """Close and free resources."""
        self.protocol.stop()

    async def connect(self):
        """Connect to the device."""
        _LOGGER.debug("Connect to Companion from API")

        srp = SRPAuthHandler()
        connection = CompanionConnection(
            self.loop, self.config.address, self.service.port
        )
        self.protocol = CompanionProtocol(connection, srp, self.service)
        await self.protocol.start()
        await self.launch_app("com.netflix.Netflix")

    async def launch_app(self, bundle_identifier: str) -> None:
        """Launch an app n the remote device."""
        if not self.protocol:
            raise Exception("not connected")  # TODO: better exception

        resp = await self.protocol.exchange_opack(
            FrameType.E_OPACK,
            {
                "_i": "_launchApp",
                "_x": 123,
                "_t": "2",
                "_c": {"_bundleID": bundle_identifier},
            },
        )

        _LOGGER.debug("Launch app response: %s", resp)
