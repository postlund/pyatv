"""Implementation of external API for AirPlay."""

import asyncio
import logging
import os
from typing import Any, Awaitable, Callable, Dict, Mapping, Optional, Set, Tuple, cast

from pyatv import conf, exceptions
from pyatv.airplay.auth import pair_verify
from pyatv.airplay.pairing import AirPlayPairingHandler
from pyatv.airplay.player import AirPlayPlayer
from pyatv.auth.hap_pairing import HapCredentials, parse_credentials
from pyatv.const import FeatureName, Protocol
from pyatv.helpers import get_unique_id
from pyatv.interface import (
    FeatureInfo,
    Features,
    FeatureState,
    PairingHandler,
    StateProducer,
    Stream,
)
from pyatv.support import mdns, net
from pyatv.support.http import (
    ClientSessionManager,
    HttpConnection,
    StaticFileWebServer,
    http_connect,
)
from pyatv.support.relayer import Relayer
from pyatv.support.scan import ScanHandler, ScanHandlerReturn

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

    def __init__(self, config: conf.AppleTV) -> None:
        """Initialize a new AirPlayStreamAPI instance."""
        self.config = config
        self.service: conf.AirPlayService = cast(
            conf.AirPlayService, self.config.get_service(Protocol.AirPlay)
        )
        self._credentials: HapCredentials = parse_credentials(self.service.credentials)
        self._play_task: Optional[asyncio.Future] = None

    def close(self) -> None:
        """Close and free resources."""
        if self._play_task is not None:
            _LOGGER.debug("Stopping AirPlay play task")
            self._play_task.cancel()
            self._play_task = None

    async def _player(self, connection: HttpConnection) -> AirPlayPlayer:
        verifier = pair_verify(self._credentials, connection)
        await verifier.verify_credentials()
        return AirPlayPlayer(connection)

    async def play_url(self, url: str, **kwargs) -> None:
        """Play media from an URL on the device.

        Note: This method will not yield until the media has finished playing.
        The Apple TV requires the request to stay open during the entire
        play duration.
        """
        if not self.service:
            raise exceptions.NotSupportedError("AirPlay service is not available")

        server: Optional[StaticFileWebServer] = None

        if os.path.exists(url):
            _LOGGER.debug("URL %s is a local file, setting up web server", url)
            server_address = net.get_local_address_reaching(self.config.address)
            server = StaticFileWebServer(url, str(server_address))
            await server.start()
            url = server.file_address

        connection: Optional[HttpConnection] = None
        try:
            connection = await http_connect(str(self.config.address), self.service.port)
            player = await self._player(connection)
            position = int(kwargs.get("position", 0))
            self._play_task = asyncio.ensure_future(player.play_url(url, position))
            return await self._play_task
        finally:
            self._play_task = None
            if connection:
                connection.close()
            if server:
                await server.close()


def airplay_service_handler(
    mdns_service: mdns.Service, response: mdns.Response
) -> ScanHandlerReturn:
    """Parse and return a new AirPlay service."""
    service = conf.AirPlayService(
        get_unique_id(mdns_service.type, mdns_service.name, mdns_service.properties),
        mdns_service.port,
        properties=mdns_service.properties,
    )
    return mdns_service.name, service


def scan() -> Mapping[str, ScanHandler]:
    """Return handlers used for scanning."""
    return {"_airplay._tcp.local": airplay_service_handler}


def setup(
    loop: asyncio.AbstractEventLoop,
    config: conf.AppleTV,
    interfaces: Dict[Any, Relayer],
    device_listener: StateProducer,
    session_manager: ClientSessionManager,
) -> Optional[
    Tuple[
        Callable[[], Awaitable[None]], Callable[[], Set[asyncio.Task]], Set[FeatureName]
    ]
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

    def _close() -> Set[asyncio.Task]:
        stream.close()
        return set()

    return _connect, _close, set([FeatureName.PlayUrl])


def pair(
    config: conf.AppleTV,
    session_manager: ClientSessionManager,
    loop: asyncio.AbstractEventLoop,
    **kwargs
) -> PairingHandler:
    """Return pairing handler for protocol."""
    return AirPlayPairingHandler(config, session_manager, loop, **kwargs)
