"""Support for audio streaming using Remote Audio Output Protocol (RAOP)."""

import asyncio
import io
import logging
import math
from typing import Any, Dict, Generator, Mapping, Optional, Set, Tuple, Union, cast

from pyatv import const, exceptions
from pyatv.auth.hap_pairing import AuthenticationType, parse_credentials
from pyatv.const import (
    DeviceModel,
    FeatureName,
    FeatureState,
    PairingRequirement,
    Protocol,
)
from pyatv.core import MutableService, SetupData, TakeoverMethod, mdns
from pyatv.core.scan import ScanHandler, ScanHandlerReturn
from pyatv.helpers import get_unique_id
from pyatv.interface import (
    Audio,
    BaseConfig,
    BaseService,
    DeviceInfo,
    FeatureInfo,
    Features,
    Metadata,
    PairingHandler,
    Playing,
    PushUpdater,
    RemoteControl,
    Stream,
)
from pyatv.protocols.airplay import service_info as airplay_service_info
from pyatv.protocols.airplay.pairing import AirPlayPairingHandler
from pyatv.protocols.airplay.utils import AirPlayFlags, parse_features
from pyatv.protocols.raop.audio_source import AudioSource, open_source
from pyatv.protocols.raop.raop import (
    PlaybackInfo,
    RaopClient,
    RaopContext,
    RaopListener,
)
from pyatv.support import map_range
from pyatv.support.collections import dict_merge
from pyatv.support.device_info import lookup_model
from pyatv.support.http import ClientSessionManager, HttpConnection, http_connect
from pyatv.support.metadata import EMPTY_METADATA, AudioMetadata, get_metadata
from pyatv.support.rtsp import RtspSession
from pyatv.support.state_producer import StateProducer

_LOGGER = logging.getLogger(__name__)

INITIAL_VOLUME = 33.0  # Percent

DBFS_MIN = -30.0
DBFS_MAX = 0.0
PERCENTAGE_MIN = 0.0
PERCENTAGE_MAX = 100.0


class RaopPushUpdater(PushUpdater):
    """Implementation of push update support for RAOP."""

    def __init__(self, metadata: Metadata, loop: asyncio.AbstractEventLoop):
        """Initialize a new RaopPushUpdater instance."""
        super().__init__(loop)
        self._activated = False
        self.metadata = metadata

    @property
    def active(self) -> bool:
        """Return if push updater has been started."""
        return self._activated

    def start(self, initial_delay: int = 0) -> None:
        """Begin to listen to updates.

        If an error occurs, start must be called again.
        """
        if self.listener is None:
            raise exceptions.NoAsyncListenerError()

        self._activated = True
        asyncio.ensure_future(self.state_updated())

    def stop(self) -> None:
        """No longer forward updates to listener."""
        self._activated = False

    async def state_updated(self):
        """State was updated, call listener."""
        try:
            playing = await self.metadata.playing()
            self.post_update(playing)
        except Exception as ex:  # pylint: disable=broad-except
            _LOGGER.debug("Playstatus error occurred: %s", ex)


class RaopPlaybackManager:
    """Manage current play state for RAOP."""

    def __init__(self, address: str, port: int) -> None:
        """Initialize a new RaopPlaybackManager instance."""
        self.playback_info: Optional[PlaybackInfo] = None
        self._is_acquired: bool = False
        self._address: str = address
        self._port: int = port
        self._context: RaopContext = RaopContext()
        self._connection: Optional[HttpConnection] = None
        self._rtsp: Optional[RtspSession] = None
        self._raop: Optional[RaopClient] = None

    @property
    def context(self) -> RaopContext:
        """Return RTSP context if a session is active."""
        return self._context

    @property
    def raop(self) -> Optional[RaopClient]:
        """Return RAOP client if a session is active."""
        return self._raop

    def acquire(self) -> None:
        """Acquire playback manager for playback."""
        if self._is_acquired:
            raise exceptions.InvalidStateError("already streaming to device")

        self._is_acquired = True

    async def setup(self) -> Tuple[RaopClient, RtspSession, RaopContext]:
        """Set up a session or return active if it exists."""
        if self._raop and self._rtsp and self._context:
            return self._raop, self._rtsp, self._context

        self._connection = await http_connect(self._address, self._port)
        self._rtsp = RtspSession(self._connection)
        self._raop = RaopClient(self._rtsp, self._context)
        return self._raop, self._rtsp, self._context

    async def teardown(self) -> None:
        """Tear down and disconnect current session."""
        if self._raop:
            self._raop.close()
        if self._connection:
            self._connection = None
        self._raop = None
        self._context.reset()
        self._rtsp = None
        self._connection = None
        self._is_acquired = False


class RaopMetadata(Metadata):
    """Implementation of metadata interface for RAOP."""

    def __init__(self, playback_manager: RaopPlaybackManager) -> None:
        """Initialize a new RaopMetadata instance."""
        self._playback_manager = playback_manager

    async def playing(self) -> Playing:
        """Return what is currently playing."""
        if self._playback_manager.playback_info is None:
            return Playing(
                device_state=const.DeviceState.Idle, media_type=const.MediaType.Unknown
            )

        metadata = self._playback_manager.playback_info.metadata
        total_time = int(metadata.duration) if metadata.duration else None
        return Playing(
            device_state=const.DeviceState.Playing,
            media_type=const.MediaType.Music,
            title=metadata.title,
            artist=metadata.artist,
            album=metadata.album,
            position=int(self._playback_manager.playback_info.position),
            total_time=total_time,
        )


class RaopFeatures(Features):
    """Implementation of supported feature functionality."""

    def __init__(self, playback_manager: RaopPlaybackManager) -> None:
        """Initialize a new RaopFeatures instance."""
        self.playback_manager = playback_manager

    def get_feature(  # pylint: disable=too-many-return-statements
        self, feature_name: FeatureName
    ) -> FeatureInfo:
        """Return current state of a feature."""
        if feature_name == FeatureName.StreamFile:
            return FeatureInfo(FeatureState.Available)

        metadata = EMPTY_METADATA
        if self.playback_manager.playback_info:
            metadata = self.playback_manager.playback_info.metadata

        if feature_name == FeatureName.Title:
            return self._availability(metadata.title)
        if feature_name == FeatureName.Artist:
            return self._availability(metadata.artist)
        if feature_name == FeatureName.Album:
            return self._availability(metadata.album)
        if feature_name in [FeatureName.Position, FeatureName.TotalTime]:
            return self._availability(metadata.duration)

        # As far as known, volume controls are always supported
        if feature_name in [
            FeatureName.SetVolume,
            FeatureName.Volume,
            FeatureName.VolumeDown,
            FeatureName.VolumeUp,
        ]:
            return FeatureInfo(FeatureState.Available)

        if feature_name == FeatureName.Stop:
            is_streaming = self.playback_manager.raop is not None
            return FeatureInfo(
                FeatureState.Available if is_streaming else FeatureState.Unavailable
            )

        return FeatureInfo(FeatureState.Unavailable)

    @staticmethod
    def _availability(value):
        return FeatureInfo(
            FeatureState.Available if value else FeatureState.Unavailable
        )


class RaopAudio(Audio):
    """Implementation of audio functionality."""

    def __init__(self, playback_manager: RaopPlaybackManager):
        """Initialize a new RaopAudio instance."""
        self.playback_manager = playback_manager

    @property
    def has_changed_volume(self) -> bool:
        """Return whether volume has changed from default or not."""
        return self.playback_manager.context.volume is not None

    @property
    def volume(self) -> float:
        """Return current volume level."""
        vol = self.playback_manager.context.volume
        if vol is None:
            return INITIAL_VOLUME

        # AirPlay uses -144.0 as "muted", but we treat everything below -30.0 as
        # muted to be a bit defensive
        if vol < DBFS_MIN:
            return PERCENTAGE_MIN

        # Map dBFS to percentage
        return map_range(vol, DBFS_MIN, DBFS_MAX, PERCENTAGE_MIN, PERCENTAGE_MAX)

    async def set_volume(self, level: float) -> None:
        """Change current volume level."""
        raop = self.playback_manager.raop

        # AirPlay uses -144.0 as muted volume, so re-map 0.0 to that
        if math.isclose(level, 0.0):
            remapped = -144.0
        else:
            # Map percentage to dBFS
            remapped = map_range(
                level, PERCENTAGE_MIN, PERCENTAGE_MAX, DBFS_MIN, DBFS_MAX
            )

        if raop:
            await raop.set_volume(remapped)
        else:
            self.playback_manager.context.volume = remapped

    async def volume_up(self) -> None:
        """Increase volume by one step."""
        await self.set_volume(min(self.volume + 5.0, 100.0))

    async def volume_down(self) -> None:
        """Decrease volume by one step."""
        await self.set_volume(max(self.volume - 5.0, 0.0))


class RaopStream(Stream):
    """Implementation of stream functionality."""

    def __init__(
        self,
        config: BaseConfig,
        service: BaseService,
        listener: RaopListener,
        audio: RaopAudio,
        playback_manager: RaopPlaybackManager,
        takeover: TakeoverMethod,
    ) -> None:
        """Initialize a new RaopStream instance."""
        self.config = config
        self.service = service
        self.listener = listener
        self.audio = audio
        self.playback_manager = playback_manager
        self.takeover = takeover

    async def stream_file(self, file: Union[str, io.BufferedReader], **kwargs) -> None:
        """Stream local file to device.

        INCUBATING METHOD - MIGHT CHANGE IN THE FUTURE!
        """
        self.playback_manager.acquire()
        audio_file: Optional[AudioSource] = None
        takeover_release = self.takeover(Audio, Metadata, PushUpdater, RemoteControl)
        try:
            client, _, context = await self.playback_manager.setup()
            client.credentials = parse_credentials(self.service.credentials)
            client.password = self.service.password

            client.listener = self.listener
            await client.initialize(self.service.properties)

            # Try to load metadata and pass it along if it succeeds
            metadata: AudioMetadata = EMPTY_METADATA
            try:
                # Source must support seeking to read metadata (or point to file)
                if isinstance(file, str) or file.seekable:
                    metadata = await get_metadata(file)
                else:
                    _LOGGER.debug(
                        "Seeking not supported by source, not loading metadata"
                    )
            except Exception as ex:
                _LOGGER.exception("Failed to extract metadata from %s: %s", file, ex)

            # After initialize has been called, all the audio properties will be
            # initialized and can be used in the miniaudio wrapper
            audio_file = await open_source(
                file,
                context.sample_rate,
                context.channels,
                context.bytes_per_channel,
            )

            # If the user didn't change volume level prior to streaming, try to extract
            # volume level from device (if supported). Otherwise set the default level
            # in pyatv.
            if not self.audio.has_changed_volume and "initialVolume" in client.info:
                initial_volume = client.info["initialVolume"]
                if not isinstance(initial_volume, float):
                    raise exceptions.ProtocolError(
                        f"initial volume {initial_volume} has "
                        "incorrect type {type(initial_volume)}",
                    )
                context.volume = initial_volume
            else:
                await self.audio.set_volume(self.audio.volume)

            await client.send_audio(audio_file, metadata)
        finally:
            takeover_release()
            if audio_file:
                await audio_file.close()
            await self.playback_manager.teardown()


class RaopRemoteControl(RemoteControl):
    """Implementation of remote control functionality."""

    def __init__(self, audio: RaopAudio, playback_manager: RaopPlaybackManager):
        """Initialize a new RaopRemoteControl instance."""
        self.audio = audio
        self.playback_manager = playback_manager

    async def stop(self) -> None:
        """Press key stop."""
        if self.playback_manager.raop:
            self.playback_manager.raop.stop()

    async def volume_up(self) -> None:
        """Press key volume up."""
        await self.audio.set_volume(min(self.audio.volume + 5.0, 100.0))

    async def volume_down(self) -> None:
        """Press key volume down."""
        await self.audio.set_volume(max(self.audio.volume - 5.0, 0.0))


def raop_service_handler(
    mdns_service: mdns.Service, response: mdns.Response
) -> Optional[ScanHandlerReturn]:
    """Parse and return a new RAOP service."""
    _, name = mdns_service.name.split("@", maxsplit=1)
    service = MutableService(
        get_unique_id(mdns_service.type, mdns_service.name, mdns_service.properties),
        Protocol.RAOP,
        mdns_service.port,
        mdns_service.properties,
    )
    return name, service


def scan() -> Mapping[str, ScanHandler]:
    """Return handlers used for scanning."""
    return {
        "_raop._tcp.local": raop_service_handler,
        "_airport._tcp.local": lambda service, response: None,
    }


def device_info(service_type: str, properties: Mapping[str, Any]) -> Dict[str, Any]:
    """Return device information from zeroconf properties."""
    devinfo: Dict[str, Any] = {}
    if "am" in properties:
        model = lookup_model(properties["am"])
        devinfo[DeviceInfo.RAW_MODEL] = properties["am"]
        if model != DeviceModel.Unknown:
            devinfo[DeviceInfo.MODEL] = model
    if "ov" in properties:
        devinfo[DeviceInfo.VERSION] = properties["ov"]

    # This comes from _airport._tcp.local and belongs to AirPort Expresses
    if "wama" in properties:
        props: Mapping[str, str] = dict(
            cast(Tuple[str, str], prop.split("=", maxsplit=1))
            for prop in ("macaddress=" + properties["wama"]).split(",")
        )
        if DeviceInfo.MAC not in devinfo:
            devinfo[DeviceInfo.MAC] = props["macaddress"].replace("-", ":").upper()
        if "syVs" in props:
            devinfo[DeviceInfo.VERSION] = props["syVs"]
    return devinfo


async def service_info(
    service: MutableService,
    devinfo: DeviceInfo,
    services: Mapping[Protocol, BaseService],
) -> None:
    """Update service with additional information."""
    airplay_service = services.get(Protocol.AirPlay)
    if airplay_service and airplay_service.properties.get("acl", "0") == "1":
        # Access control might say that pairing is not possible, e.g. only devices
        # belonging to the same home (not supported by pyatv)
        service.pairing = PairingRequirement.Disabled
    else:
        # Same behavior as for AirPlay expected, so re-using that here
        await airplay_service_info(service, devinfo, services)


def setup(  # pylint: disable=too-many-locals
    loop: asyncio.AbstractEventLoop,
    config: BaseConfig,
    service: BaseService,
    device_listener: StateProducer,
    session_manager: ClientSessionManager,
    takeover: TakeoverMethod,
) -> Generator[SetupData, None, None]:
    """Set up a new RAOP service."""
    playback_manager = RaopPlaybackManager(str(config.address), service.port)
    metadata = RaopMetadata(playback_manager)
    push_updater = RaopPushUpdater(metadata, loop)

    class RaopStateListener(RaopListener):
        """Listener for RAOP state changes."""

        def playing(self, playback_info: PlaybackInfo) -> None:
            """Media started playing with metadata."""
            playback_manager.playback_info = playback_info
            self._trigger()

        def stopped(self) -> None:
            """Media stopped playing."""
            playback_manager.playback_info = None
            self._trigger()

        @staticmethod
        def _trigger():
            """Trigger push update."""
            if push_updater.active:
                asyncio.ensure_future(push_updater.state_updated())

    raop_listener = RaopStateListener()
    raop_audio = RaopAudio(playback_manager)

    interfaces = {
        Stream: RaopStream(
            config, service, raop_listener, raop_audio, playback_manager, takeover
        ),
        Features: RaopFeatures(playback_manager),
        PushUpdater: push_updater,
        Metadata: metadata,
        Audio: raop_audio,
        RemoteControl: RaopRemoteControl(raop_audio, playback_manager),
    }

    async def _connect() -> bool:
        return True

    def _close() -> Set[asyncio.Task]:
        return set()

    def _device_info() -> Dict[str, Any]:
        devinfo: Dict[str, Any] = {}
        for service_type in scan():
            properties = config.properties.get(service_type)
            if properties:
                dict_merge(devinfo, device_info(service_type, properties))
        return devinfo

    yield SetupData(
        Protocol.RAOP,
        _connect,
        _close,
        _device_info,
        interfaces,
        set(
            [
                FeatureName.StreamFile,
                FeatureName.PushUpdates,
                FeatureName.Artist,
                FeatureName.Album,
                FeatureName.Title,
                FeatureName.Position,
                FeatureName.TotalTime,
                FeatureName.SetVolume,
                FeatureName.Volume,
                FeatureName.VolumeUp,
                FeatureName.VolumeDown,
                FeatureName.Stop,
            ]
        ),
    )


def pair(
    config: BaseConfig,
    service: BaseService,
    session_manager: ClientSessionManager,
    loop: asyncio.AbstractEventLoop,
    **kwargs
) -> PairingHandler:
    """Return pairing handler for protocol."""
    features = service.properties.get("ft")
    if not features:
        # TODO: Better handle cases like these (provide API)
        raise exceptions.NotSupportedError("pairing not required")

    flags = parse_features(features)
    if AirPlayFlags.SupportsLegacyPairing not in flags:
        raise exceptions.NotSupportedError("legacy pairing not supported")

    return AirPlayPairingHandler(
        config, service, session_manager, AuthenticationType.Legacy, **kwargs
    )
