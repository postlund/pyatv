"""Implementation of external API for AirPlay."""

import os
import re
import asyncio
import logging
import binascii

from aiohttp import ClientSession

from pyatv import exceptions
from pyatv.const import Protocol
from pyatv.interface import Stream
from pyatv.support import net

from pyatv.airplay.player import AirPlayPlayer
from pyatv.airplay.srp import SRPAuthHandler
from pyatv.airplay.auth import AuthenticationVerifier
from pyatv.airplay.server import StaticFileWebServer

_LOGGER = logging.getLogger(__name__)


class AirPlayStreamAPI(Stream):  # pylint: disable=too-few-public-methods
    """Implementation of stream API with AirPlay."""

    def __init__(self, config, loop: asyncio.AbstractEventLoop) -> None:
        """Initialize a new AirPlayStreamAPI instance."""
        self.config = config
        self.loop = loop
        self.service = self.config.get_service(Protocol.AirPlay)
        self.identifier = None
        self.credentials = self._get_credentials()
        self._play_task = None

    def close(self) -> None:
        """Close and free resources."""
        if self._play_task is not None:
            _LOGGER.debug("Stopping AirPlay play task")
            self._play_task.cancel()
            self._play_task = None

    def _get_credentials(self):
        if not self.service or self.service.credentials is None:
            _LOGGER.debug("No AirPlay credentials loaded")
            return None

        if not re.match(r"[0-9A-Fa-f]{16}:[0-9A-Fa-f]{64}", self.service.credentials):
            raise exceptions.InvalidCredentialsError(
                f"invalid credentials: {self.service.credentials}"
            )

        split = self.service.credentials.split(":")
        _LOGGER.debug("Loaded AirPlay credentials: %s", self.service.credentials)

        return split[1]

    async def _player(self, session: ClientSession) -> AirPlayPlayer:
        http = net.HttpSession(
            session, f"http://{self.config.address}:{self.service.port}/"
        )
        player = AirPlayPlayer(self.loop, http)

        # If credentials have been loaded, do device verification first
        if self.credentials:
            srp = SRPAuthHandler()
            srp.initialize(binascii.unhexlify(self.credentials))
            verifier = AuthenticationVerifier(http, srp)
            await verifier.verify_authed()

        return player

    async def play_url(self, url, **kwargs):
        """Play media from an URL on the device.

        Note: This method will not yield until the media has finished playing.
        The Apple TV requires the request to stay open during the entire
        play duration.
        """
        if not self.service:
            raise exceptions.NotSupportedError("AirPlay service is not available")

        server = None

        if os.path.exists(url):
            _LOGGER.debug("URL %s is a local file, setting up web server", url)
            server_address = net.get_local_address_reaching(self.config.address)
            server = StaticFileWebServer(url, server_address)
            await server.start()
            url = server.file_address

        # This creates a new ClientSession every time something is played.
        # It is not recommended by aiohttp, but it is the only way not having
        # a dangling connection laying around. So it will have to do for now.
        session_manager = await net.create_session()
        try:
            player = await self._player(session_manager.session)
            position = int(kwargs.get("position", 0))
            self._play_task = asyncio.ensure_future(player.play_url(url, position))
            return await self._play_task
        finally:
            self._play_task = None
            await session_manager.close()
            if server:
                await server.close()
