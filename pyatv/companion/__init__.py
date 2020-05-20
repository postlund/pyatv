"""PoC code for Companion protocol."""

import os
import re
import asyncio
import logging
import binascii

from pyatv import exceptions
from pyatv.const import Protocol

from pyatv.companion.connection import CompanionConnection
from pyatv.companion.auth import CompanionPairingVerifier
from pyatv.companion.protocol import CompanionProtocol
from pyatv.companion.srp import SRPAuthHandler

_LOGGER = logging.getLogger(__name__)


class CompanionAPI:
    """Implementation of companion API."""

    def __init__(self, config, loop):
        """Initialize a new AirPlayStreamAPI instance."""
        self.config = config
        self.loop = loop
        self.service = self.config.get_service(Protocol.Companion)

    def close(self):
        """Close and free resources."""

    async def connect(self):
        """Dummy code to test connection."""
        _LOGGER.debug("Connect to Companion from API")

        srp = SRPAuthHandler()
        connection = CompanionConnection(
            self.loop, self.config.address, self.service.port
        )
        protocol = CompanionProtocol(connection, srp, self.service)
        await protocol.start()
