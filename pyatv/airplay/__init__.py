"""Implementation of external API for AirPlay."""

import asyncio
import logging
import os
from typing import Any, Dict, Generator, Mapping, Optional, Set, cast

from pyatv import conf, exceptions, mrp
from pyatv.airplay import remote_control
from pyatv.airplay.auth import extract_credentials, verify_connection
from pyatv.airplay.mrp_connection import AirPlayMrpConnection
from pyatv.airplay.pairing import AirPlayPairingHandler, get_preferred_auth_type
from pyatv.airplay.player import AirPlayPlayer
from pyatv.auth.hap_pairing import AuthenticationType, HapCredentials, parse_credentials
from pyatv.const import DeviceModel, FeatureName, Protocol
from pyatv.core import SetupData
from pyatv.helpers import get_unique_id
from pyatv.interface import (
    BaseService,
    DeviceInfo,
    FeatureInfo,
    Features,
    FeatureState,
    PairingHandler,
    StateProducer,
    Stream,
)
from pyatv.support import mdns, net
from pyatv.support.device_info import lookup_model
from pyatv.support.http import (
    ClientSessionManager,
    HttpConnection,
    StaticFileWebServer,
    http_connect,
)
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
            # Connect and verify connection to set up encryption
            connection = await http_connect(str(self.config.address), self.service.port)
            await verify_connection(self._credentials, connection)

            player = AirPlayPlayer(connection)
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


def device_info(properties: Mapping[str, Any]) -> Dict[str, Any]:
    """Return device information from zeroconf properties."""
    devinfo: Dict[str, Any] = {}
    if "model" in properties:
        model = lookup_model(properties["model"])
        if model != DeviceModel.Unknown:
            devinfo[DeviceInfo.MODEL] = lookup_model(properties["model"])
    if "osvers" in properties:
        devinfo[DeviceInfo.VERSION] = properties["osvers"]
    if "deviceid" in properties:
        devinfo[DeviceInfo.MAC] = properties["deviceid"]
    return devinfo


def setup(  # pylint: disable=too-many-locals
    loop: asyncio.AbstractEventLoop,
    config: conf.AppleTV,
    service: BaseService,
    device_listener: StateProducer,
    session_manager: ClientSessionManager,
) -> Generator[SetupData, None, None]:
    """Set up a new AirPlay service."""
    # TODO: Split up in connect/protocol and Stream implementation
    stream = AirPlayStream(config)

    interfaces = {
        Features: AirPlayFeatures(cast(conf.AirPlayService, service)),
        Stream: stream,
    }

    async def _connect() -> bool:
        return True

    def _close() -> Set[asyncio.Task]:
        stream.close()
        return set()

    def _device_info() -> Dict[str, Any]:
        return device_info(service.properties)

    yield SetupData(
        Protocol.AirPlay,
        _connect,
        _close,
        _device_info,
        interfaces,
        set([FeatureName.PlayUrl]),
    )

    credentials = extract_credentials(service)

    # Set up remote control channel if it is supported
    if not remote_control.is_supported(service):
        _LOGGER.debug("Remote control not supported by device")
    elif credentials.type not in [AuthenticationType.HAP, AuthenticationType.Transient]:
        _LOGGER.debug("%s not supported by remote control channel", credentials.type)
    else:
        _LOGGER.debug("Remote control channel is supported")

        control = remote_control.RemoteControl(device_listener)
        control_port = service.port

        # When tunneling, we don't have any identifier or port available at this stage
        mrp_service = conf.MrpService(None, 0)
        config.add_service(mrp_service)
        (
            _,
            mrp_connect,
            mrp_close,
            mrp_device_info,
            mrp_interfaces,
            mrp_features,
        ) = mrp.create_with_connection(
            loop,
            config,
            mrp_service,
            device_listener,
            session_manager,
            AirPlayMrpConnection(control, device_listener),
            requires_heatbeat=False,  # Already have heartbeat on control channel
        )

        async def _connect_rc() -> bool:
            try:

                await control.start(str(config.address), control_port, credentials)
            except Exception as ex:
                _LOGGER.warning("Failed to set up remote control channel: %s", ex)
                return False
            else:
                await mrp_connect()
            return True

        def _close_rc() -> Set[asyncio.Task]:
            tasks = set()
            tasks.update(mrp_close())
            tasks.update(control.stop())
            return tasks

        yield SetupData(
            Protocol.MRP,
            _connect_rc,
            _close_rc,
            mrp_device_info,
            mrp_interfaces,
            mrp_features,
        )


def pair(
    config: conf.AppleTV,
    service: BaseService,
    session_manager: ClientSessionManager,
    loop: asyncio.AbstractEventLoop,
    **kwargs
) -> PairingHandler:
    """Return pairing handler for protocol."""
    return AirPlayPairingHandler(
        config, service, session_manager, get_preferred_auth_type(service), **kwargs
    )
