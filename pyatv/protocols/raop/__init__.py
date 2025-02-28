"""Support for audio streaming using Remote Audio Output Protocol (RAOP)."""

import asyncio
import io
import logging
from typing import Any, Dict, Generator, Mapping, Optional, Set, Tuple, Union, cast

from pyatv import const, exceptions
from pyatv.const import (
    DeviceModel,
    FeatureName,
    FeatureState,
    OperatingSystem,
    PairingRequirement,
    Protocol,
)
from pyatv.core import (
    AbstractPushUpdater,
    Core,
    MutableService,
    ProtocolStateDispatcher,
    SetupData,
    StateMessage,
    UpdatedState,
    mdns,
)
from pyatv.core.scan import (
    ScanHandlerDeviceInfoName,
    ScanHandlerReturn,
    device_info_name_from_unique_short_name,
)
from pyatv.helpers import get_unique_id
from pyatv.interface import (
    Audio,
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
from pyatv.protocols.airplay.auth import extract_credentials
from pyatv.protocols.airplay.pairing import AirPlayPairingHandler
from pyatv.protocols.airplay.utils import (
    AirPlayMajorVersion,
    dbfs_to_pct,
    get_protocol_version,
    pct_to_dbfs,
    update_service_details,
)
from pyatv.protocols.raop.audio_source import AudioSource, open_source
from pyatv.protocols.raop.protocols import StreamContext, airplayv1, airplayv2
from pyatv.protocols.raop.stream_client import PlaybackInfo, RaopListener, StreamClient
from pyatv.support.collections import dict_merge
from pyatv.support.device_info import lookup_model, lookup_os
from pyatv.support.http import HttpConnection, http_connect
from pyatv.support.metadata import EMPTY_METADATA, MediaMetadata, merge_into
from pyatv.support.rtsp import RtspSession

_LOGGER = logging.getLogger(__name__)

INITIAL_VOLUME = 33.0  # Percent


class RaopPushUpdater(AbstractPushUpdater):
    """Implementation of push update support for RAOP."""

    def __init__(self, metadata: Metadata, state_dispatcher: ProtocolStateDispatcher):
        """Initialize a new RaopPushUpdater instance."""
        super().__init__(state_dispatcher)
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

    def __init__(self, core: Core) -> None:
        """Initialize a new RaopPlaybackManager instance."""
        self.core = core
        self.playback_info: Optional[PlaybackInfo] = None
        self._is_acquired: bool = False
        self._context: StreamContext = StreamContext()
        self._connection: Optional[HttpConnection] = None
        self._rtsp: Optional[RtspSession] = None
        self._stream_client: Optional[StreamClient] = None

    @property
    def context(self) -> StreamContext:
        """Return RTSP context if a session is active."""
        return self._context

    @property
    def stream_client(self) -> Optional[StreamClient]:
        """Return stream client if a session is active."""
        return self._stream_client

    def acquire(self) -> None:
        """Acquire playback manager for playback."""
        if self._is_acquired:
            raise exceptions.InvalidStateError("already streaming to device")

        self._is_acquired = True

    async def setup(self, service: BaseService) -> Tuple[StreamClient, StreamContext]:
        """Set up a session or return active if it exists."""
        if self._stream_client and self._rtsp and self._context:
            return self._stream_client, self._context

        self._connection = await http_connect(
            str(self.core.config.address), self.core.service.port
        )
        self._rtsp = RtspSession(self._connection)

        protocol_version = get_protocol_version(
            service, self.core.settings.protocols.raop.protocol_version
        )
        _LOGGER.debug("Using AirPlay version %s", protocol_version)

        protocol_class = (
            airplayv1.AirPlayV1
            if protocol_version == AirPlayMajorVersion.AirPlayV1
            else airplayv2.AirPlayV2
        )

        self._stream_client = StreamClient(
            self._rtsp,
            self._context,
            protocol_class(self._context, self._rtsp),
            self.core.settings,
        )
        return self._stream_client, self._context

    async def teardown(self) -> None:
        """Tear down and disconnect current session."""
        if self._stream_client:
            self._stream_client.close()
        if self._connection:
            self._connection.close()
            self._connection = None
        self._stream_client = None
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

        if feature_name in [FeatureName.Stop, FeatureName.Pause]:
            is_streaming = self.playback_manager.stream_client is not None
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

    def __init__(
        self,
        playback_manager: RaopPlaybackManager,
        state_dispatcher: ProtocolStateDispatcher,
    ):
        """Initialize a new RaopAudio instance."""
        self.playback_manager = playback_manager
        self.state_dispatcher = state_dispatcher
        self.state_dispatcher.listen_to(UpdatedState.Volume, self._volume_changed)

    # Intercept volume changes by other protocols and update accordingly. We blindly
    # blindly trust any volume we see here as it's a much better guess than we have.
    def _volume_changed(self, message: StateMessage) -> None:
        """State of something changed."""
        volume = cast(float, message.value)

        _LOGGER.debug("Protocol %s changed volume to %f", message.protocol.name, volume)
        self.playback_manager.context.volume = pct_to_dbfs(volume)

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

        return dbfs_to_pct(vol)

    async def set_volume(self, level: float) -> None:
        """Change current volume level."""
        raop = self.playback_manager.stream_client
        dbfs_volume = pct_to_dbfs(level)

        if raop:
            await raop.set_volume(dbfs_volume)
        else:
            self.playback_manager.context.volume = dbfs_volume

        self.state_dispatcher.dispatch(UpdatedState.Volume, self.volume)

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
        core: Core,
        listener: RaopListener,
        audio: RaopAudio,
        playback_manager: RaopPlaybackManager,
    ) -> None:
        """Initialize a new RaopStream instance."""
        self.core = core
        self.listener = listener
        self.audio = audio
        self.playback_manager = playback_manager

    async def stream_file(
        self,
        file: Union[str, io.BufferedIOBase, asyncio.streams.StreamReader],
        /,
        metadata: Optional[MediaMetadata] = None,
        override_missing_metadata: bool = False,
        **kwargs
    ) -> None:
        """Stream local or remote file to device.

        Supports either local file paths or a HTTP(s) address.

        INCUBATING METHOD - MIGHT CHANGE IN THE FUTURE!
        """
        self.playback_manager.acquire()
        audio_file: Optional[AudioSource] = None
        takeover_release = self.core.takeover(
            Audio, Metadata, PushUpdater, RemoteControl
        )
        try:
            client, context = await self.playback_manager.setup(self.core.service)
            context.credentials = extract_credentials(self.core.service)
            context.password = self.core.service.password

            client.listener = self.listener
            await client.initialize(self.core.service.properties)

            # After initialize has been called, all the audio properties will be
            # initialized and can be used in the miniaudio wrapper
            audio_file = await open_source(
                file,
                context.sample_rate,
                context.channels,
                context.bytes_per_channel,
            )

            # If no custom metadata is provided, try to load from source. If it is
            # provided, check if metadata should be overridden or not.
            if metadata is None:
                file_metadata = await audio_file.get_metadata()
            elif override_missing_metadata:
                file_metadata = await audio_file.get_metadata()
                file_metadata = merge_into(file_metadata, metadata)
            else:
                file_metadata = metadata

            # If the user didn't change volume level prior to streaming, try to extract
            # volume level from device (if supported). Otherwise set the default level
            # in pyatv.
            volume = None
            if not self.audio.has_changed_volume and "initialVolume" in client.info:
                initial_volume = client.info["initialVolume"]
                if not isinstance(initial_volume, float):
                    raise exceptions.ProtocolError(
                        f"initial volume {initial_volume} has "
                        "incorrect type {type(initial_volume)}",
                    )
                context.volume = initial_volume
            else:
                # Try to set volume. If it fails, defer to setting it once
                # streaming has started.
                try:
                    await self.audio.set_volume(self.audio.volume)
                except Exception as ex:
                    _LOGGER.debug("Failed to set volume (%s), delaying call", ex)
                    volume = self.audio.volume

            await client.send_audio(audio_file, file_metadata, volume=volume)
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

    # At the moment, pause will stop playback until it is properly implemented. This
    # gives a better experience in Home Assistant.
    async def pause(self) -> None:
        """Press key pause."""
        if self.playback_manager.stream_client:
            self.playback_manager.stream_client.stop()

    async def stop(self) -> None:
        """Press key stop."""
        if self.playback_manager.stream_client:
            self.playback_manager.stream_client.stop()

    async def volume_up(self) -> None:
        """Press key volume up."""
        await self.audio.set_volume(min(self.audio.volume + 5.0, 100.0))

    async def volume_down(self) -> None:
        """Press key volume down."""
        await self.audio.set_volume(max(self.audio.volume - 5.0, 0.0))


def raop_name_from_service_name(service_name: str) -> str:
    """Convert an raop service name to a name."""
    split = service_name.split("@", maxsplit=1)
    return split[1] if len(split) == 2 else split[0]


def raop_service_handler(
    mdns_service: mdns.Service, response: mdns.Response
) -> Optional[ScanHandlerReturn]:
    """Parse and return a new RAOP service."""
    name = raop_name_from_service_name(mdns_service.name)
    service = MutableService(
        get_unique_id(mdns_service.type, mdns_service.name, mdns_service.properties),
        Protocol.RAOP,
        mdns_service.port,
        mdns_service.properties,
    )
    return name, service


def scan() -> Mapping[str, ScanHandlerDeviceInfoName]:
    """Return handlers used for scanning."""
    return {
        "_raop._tcp.local": (raop_service_handler, raop_name_from_service_name),
        "_airport._tcp.local": (
            lambda service, response: None,
            device_info_name_from_unique_short_name,
        ),
    }


def device_info(service_type: str, properties: Mapping[str, Any]) -> Dict[str, Any]:
    """Return device information from zeroconf properties."""
    devinfo: Dict[str, Any] = {}
    if "am" in properties:
        model = lookup_model(properties["am"])
        devinfo[DeviceInfo.RAW_MODEL] = properties["am"]
        if model != DeviceModel.Unknown:
            devinfo[DeviceInfo.MODEL] = model
        operating_system = lookup_os(properties["am"])
        if operating_system != OperatingSystem.Unknown:
            devinfo[DeviceInfo.OPERATING_SYSTEM] = operating_system
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
    elif airplay_service and airplay_service.properties.get("act", "0") == "2":
        # Similarly to ACL, we can have an access control type we do not support,
        # e.g. "2" which corresponds to "Current User". So we need to filter that.
        service.pairing = PairingRequirement.Unsupported
    else:
        # Same behavior as for AirPlay expected, so reusing that here
        update_service_details(service)


def setup(  # pylint: disable=too-many-locals
    core: Core,
) -> Generator[SetupData, None, None]:
    """Set up a new RAOP service."""
    playback_manager = RaopPlaybackManager(core)
    metadata = RaopMetadata(playback_manager)
    push_updater = RaopPushUpdater(metadata, core.state_dispatcher)

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
    raop_audio = RaopAudio(playback_manager, core.state_dispatcher)

    interfaces = {
        Stream: RaopStream(core, raop_listener, raop_audio, playback_manager),
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
            properties = core.config.properties.get(service_type)
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
                FeatureName.Pause,
            ]
        ),
    )


def pair(core: Core, **kwargs) -> PairingHandler:
    """Return pairing handler for protocol."""
    return AirPlayPairingHandler(
        core,
        get_protocol_version(
            core.service, core.settings.protocols.raop.protocol_version
        ),
        **kwargs,
    )
