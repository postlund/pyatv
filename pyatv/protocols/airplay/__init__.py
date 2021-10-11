"""Implementation of external API for AirPlay."""

import asyncio
import logging
import os
from typing import Any, Dict, Generator, Mapping, Optional, Set

from pyatv import exceptions
from pyatv.auth.hap_pairing import AuthenticationType, HapCredentials, parse_credentials
from pyatv.const import DeviceModel, FeatureName, PairingRequirement, Protocol
from pyatv.core import MutableService, SetupData, TakeoverMethod, mdns
from pyatv.core.scan import ScanHandler, ScanHandlerReturn
from pyatv.helpers import get_unique_id
from pyatv.interface import (
    BaseConfig,
    BaseService,
    DeviceInfo,
    FeatureInfo,
    Features,
    FeatureState,
    PairingHandler,
    Stream,
)
from pyatv.protocols import mrp
from pyatv.protocols.airplay.auth import extract_credentials, verify_connection
from pyatv.protocols.airplay.mrp_connection import AirPlayMrpConnection
from pyatv.protocols.airplay.pairing import (
    AirPlayPairingHandler,
    get_preferred_auth_type,
)
from pyatv.protocols.airplay.player import AirPlayPlayer
from pyatv.protocols.airplay.remote_control import RemoteControl
from pyatv.protocols.airplay.utils import (
    AirPlayFlags,
    get_pairing_requirement,
    is_password_required,
    is_remote_control_supported,
    parse_features,
)
from pyatv.support import net
from pyatv.support.device_info import lookup_model
from pyatv.support.http import (
    ClientSessionManager,
    HttpConnection,
    StaticFileWebServer,
    http_connect,
)
from pyatv.support.state_producer import StateProducer

_LOGGER = logging.getLogger(__name__)


class AirPlayFeatures(Features):
    """Implementation of supported feature functionality."""

    def __init__(self, service: BaseService) -> None:
        """Initialize a new AirPlayFeatures instance."""
        self.service = service
        self._features = parse_features(self.service.properties.get("features", "0x0"))

    def get_feature(self, feature_name: FeatureName) -> FeatureInfo:
        """Return current state of a feature."""
        if feature_name == FeatureName.PlayUrl and (
            AirPlayFlags.SupportsAirPlayVideoV1 in self._features
            or AirPlayFlags.SupportsAirPlayVideoV2 in self._features
        ):
            return FeatureInfo(FeatureState.Available)

        return FeatureInfo(FeatureState.Unavailable)


class AirPlayStream(Stream):  # pylint: disable=too-few-public-methods
    """Implementation of stream API with AirPlay."""

    def __init__(self, config: BaseConfig, service: BaseService) -> None:
        """Initialize a new AirPlayStreamAPI instance."""
        self.config = config
        self.service = service
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
) -> Optional[ScanHandlerReturn]:
    """Parse and return a new AirPlay service."""
    service = MutableService(
        get_unique_id(mdns_service.type, mdns_service.name, mdns_service.properties),
        Protocol.AirPlay,
        mdns_service.port,
        properties=mdns_service.properties,
    )
    return mdns_service.name, service


def scan() -> Mapping[str, ScanHandler]:
    """Return handlers used for scanning."""
    return {"_airplay._tcp.local": airplay_service_handler}


def device_info(service_type: str, properties: Mapping[str, Any]) -> Dict[str, Any]:
    """Return device information from zeroconf properties."""
    devinfo: Dict[str, Any] = {}
    if "model" in properties:
        model = lookup_model(properties["model"])
        devinfo[DeviceInfo.RAW_MODEL] = properties["model"]
        if model != DeviceModel.Unknown:
            devinfo[DeviceInfo.MODEL] = model
    if "osvers" in properties:
        devinfo[DeviceInfo.VERSION] = properties["osvers"]
    if "deviceid" in properties:
        devinfo[DeviceInfo.MAC] = properties["deviceid"]
    return devinfo


async def service_info(
    service: MutableService,
    devinfo: DeviceInfo,
    services: Mapping[Protocol, BaseService],
) -> None:
    """Update service with additional information."""
    service.requires_password = is_password_required(service)

    if service.properties.get("acl", "0") == "1":
        # Access control might say that pairing is not possible, e.g. only devices
        # belonging to the same home (not supported by pyatv)
        service.pairing = PairingRequirement.Disabled
    elif devinfo.model in [
        DeviceModel.AirPortExpressGen2,
        DeviceModel.HomePod,
        DeviceModel.HomePodMini,
    ]:
        # Some devices require no pairing at all, so exclude them
        service.pairing = PairingRequirement.NotNeeded
    else:
        service.pairing = get_pairing_requirement(service)


def setup(  # pylint: disable=too-many-locals
    loop: asyncio.AbstractEventLoop,
    config: BaseConfig,
    service: BaseService,
    device_listener: StateProducer,
    session_manager: ClientSessionManager,
    takeover: TakeoverMethod,
) -> Generator[SetupData, None, None]:
    """Set up a new AirPlay service."""
    # TODO: Split up in connect/protocol and Stream implementation
    stream = AirPlayStream(config, service)

    interfaces = {
        Features: AirPlayFeatures(service),
        Stream: stream,
    }

    async def _connect() -> bool:
        return True

    def _close() -> Set[asyncio.Task]:
        stream.close()
        return set()

    def _device_info() -> Dict[str, Any]:
        return device_info(list(scan().keys())[0], service.properties)

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
    if not is_remote_control_supported(service):
        _LOGGER.debug("Remote control not supported by device")
    elif credentials.type not in [AuthenticationType.HAP, AuthenticationType.Transient]:
        _LOGGER.debug("%s not supported by remote control channel", credentials.type)
    else:
        _LOGGER.debug("Remote control channel is supported")

        control = RemoteControl(device_listener)
        control_port = service.port

        # When tunneling, we don't have any identifier or port available at this stage
        mrp_service = MutableService(None, Protocol.MRP, 0, {})
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
            takeover,
            AirPlayMrpConnection(control, device_listener),
            requires_heatbeat=False,  # Already have heartbeat on control channel
        )

        async def _connect_rc() -> bool:
            try:

                await control.start(str(config.address), control_port, credentials)
            except exceptions.HttpError as ex:
                if ex.status_code == 470:
                    _LOGGER.debug(
                        "Remote control authorization failed, missing credentials"
                    )
                else:
                    _LOGGER.exception("Failed to set up remote control channel")
            except Exception:
                _LOGGER.exception("Failed to set up remote control channel")
            else:
                await mrp_connect()
                return True
            return False

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
    config: BaseConfig,
    service: BaseService,
    session_manager: ClientSessionManager,
    loop: asyncio.AbstractEventLoop,
    **kwargs
) -> PairingHandler:
    """Return pairing handler for protocol."""
    return AirPlayPairingHandler(
        config, service, session_manager, get_preferred_auth_type(service), **kwargs
    )
