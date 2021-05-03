"""Implementation of external API for AirPlay."""

import asyncio
import binascii
import logging
import os
import re
from typing import Any, Awaitable, Callable, Dict, Optional, Set, Tuple, cast

from aiohttp import ClientSession

from pyatv import conf, exceptions
from pyatv.airplay.auth import AuthenticationVerifier
from pyatv.airplay.player import AirPlayPlayer
from pyatv.airplay.server import StaticFileWebServer
from pyatv.airplay.srp import SRPAuthHandler
from pyatv.const import FeatureName, Protocol
from pyatv.interface import FeatureInfo, Features, FeatureState, StateProducer, Stream
from pyatv.support import net
from pyatv.support.net import ClientSessionManager
from pyatv.support.relayer import Relayer

_LOGGER = logging.getLogger(__name__)


class AirPlayFeatures(Features):
    """Implementation of supported feature functionality."""

    def __init__(self, service: conf.AirPlayService) -> None:
        """Initialize a new AirPlayFeatures instance."""
        self.service = service

    def get_feature(self, feature_name: FeatureName) -> FeatureInfo:
        """Return current state of a feature."""
        has_credentials = self.service.credentials
        if feature_name == FeatureName.PlayUrl and has_credentials:
            return FeatureInfo(FeatureState.Available)

        return FeatureInfo(FeatureState.Unavailable)


class AirPlayStream(Stream):  # pylint: disable=too-few-public-methods
    """Implementation of stream API with AirPlay."""

    def __init__(self, config) -> None:
        """Initialize a new AirPlayStreamAPI instance."""
        self.config = config
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
        player = AirPlayPlayer(http)

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


def setup(
    loop: asyncio.AbstractEventLoop,
    config: conf.AppleTV,
    interfaces: Dict[Any, Relayer],
    device_listener: StateProducer,
    session_manager: ClientSessionManager,
) -> Optional[
    Tuple[Callable[[], Awaitable[None]], Callable[[], None], Set[FeatureName]]
]:
    """Set up a new AirPlay service."""
    service = config.get_service(Protocol.AirPlay)
    assert service is not None

    # TODO: Split up in connect/protocol and Stream implementation
    stream = AirPlayStream(config)

    interfaces[Features].register(
        AirPlayFeatures(cast(conf.AirPlayService, service)), Protocol.AirPlay
    )
    interfaces[Stream].register(stream, Protocol.AirPlay)

    async def _connect() -> None:
        pass

    def _close() -> None:
        stream.close()

    return _connect, _close, set([FeatureName.PlayUrl])
