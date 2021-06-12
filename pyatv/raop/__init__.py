"""Support for audio streaming using Remote Audio Output Protocol (RAOP)."""

import asyncio
import logging
from typing import Any, Awaitable, Callable, Dict, Optional, Set, Tuple, cast

from pyatv import conf, const, exceptions
from pyatv.airplay.srp import LegacyCredentials
from pyatv.const import FeatureName, FeatureState, Protocol
from pyatv.interface import (
    Audio,
    FeatureInfo,
    Features,
    Metadata,
    Playing,
    PushUpdater,
    StateProducer,
    Stream,
)
from pyatv.raop.metadata import EMPTY_METADATA, AudioMetadata, get_metadata
from pyatv.raop.miniaudio import MiniaudioWrapper
from pyatv.raop.raop import PlaybackInfo, RaopClient, RaopListener
from pyatv.raop.rtsp import RtspContext, RtspSession
from pyatv.support import map_range
from pyatv.support.http import ClientSessionManager, http_connect
from pyatv.support.relayer import Relayer

_LOGGER = logging.getLogger(__name__)

INITIAL_VOLUME = 33.0


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
        asyncio.ensure_future(self.state_updated(), loop=self.loop)

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


class RaopStateManager:
    """Manage current play state for RAOP."""

    def __init__(self) -> None:
        """Initialize a new RaopStateManager instance."""
        self.playback_info: Optional[PlaybackInfo] = None


class RaopMetadata(Metadata):
    """Implementation of metadata interface for RAOP."""

    def __init__(self, state_manager: RaopStateManager) -> None:
        """Initialize a new RaopMetadata instance."""
        self._state_manager = state_manager

    async def playing(self) -> Playing:
        """Return what is currently playing."""
        if self._state_manager.playback_info is None:
            return Playing(
                device_state=const.DeviceState.Idle, media_type=const.MediaType.Unknown
            )

        metadata = self._state_manager.playback_info.metadata
        total_time = int(metadata.duration) if metadata.duration else None
        return Playing(
            device_state=const.DeviceState.Playing,
            media_type=const.MediaType.Music,
            title=metadata.title,
            artist=metadata.artist,
            album=metadata.album,
            position=int(self._state_manager.playback_info.position),
            total_time=total_time,
        )


class RaopFeatures(Features):
    """Implementation of supported feature functionality."""

    def __init__(self, state_manager: RaopStateManager) -> None:
        """Initialize a new RaopFeatures instance."""
        self.state_manager = state_manager

    def get_feature(self, feature_name: FeatureName) -> FeatureInfo:
        """Return current state of a feature."""
        if feature_name == FeatureName.StreamFile:
            return FeatureInfo(FeatureState.Available)

        metadata = EMPTY_METADATA
        if self.state_manager.playback_info:
            metadata = self.state_manager.playback_info.metadata

        if feature_name == FeatureName.Title:
            return self._availability(metadata.title)
        if feature_name == FeatureName.Artist:
            return self._availability(metadata.artist)
        if feature_name == FeatureName.Album:
            return self._availability(metadata.album)
        if feature_name in [FeatureName.Position, FeatureName.TotalTime]:
            return self._availability(metadata.duration)

        # As far as known, volume controls are always supported
        if feature_name in [FeatureName.SetVolume, FeatureName.Volume, FeatureName]:
            return FeatureInfo(FeatureState.Available)

        return FeatureInfo(FeatureState.Unavailable)

    @staticmethod
    def _availability(value):
        return FeatureInfo(
            FeatureState.Available if value else FeatureState.Unavailable
        )


class RaopAudio(Audio):
    """Implementation of audio functionality."""

    def __init__(self):
        """Initialize a new RaopAudio instance."""
        self._volume: Optional[float] = None

    @property
    def has_changed_volume(self) -> bool:
        """Return whether volume has changed from default or not."""
        return self._volume is not None

    @property
    def volume(self) -> float:
        """Return current volume level."""
        return self._volume or INITIAL_VOLUME

    async def set_volume(self, level: float) -> None:
        """Change current volume level."""
        self._volume = level


class RaopStream(Stream):
    """Implementation of stream functionality."""

    def __init__(
        self,
        address: str,
        service: conf.RaopService,
        listener: RaopListener,
        audio: RaopAudio,
    ) -> None:
        """Initialize a new RaopStream instance."""
        self.address = address
        self.service = service
        self.listener = listener
        self.audio = audio

    async def stream_file(self, filename: str, **kwargs) -> None:
        """Stream local file to device.

        INCUBATING METHOD - MIGHT CHANGE IN THE FUTURE!
        """
        connection = await http_connect(self.address, self.service.port)
        context = RtspContext()
        session = RtspSession(connection, context)

        # For now, we hi-jack credentials from AirPlay (even though they are passed via
        # the RAOP service) and use the same verification procedure as AirPlay, since
        # it's the same in practice.
        credentials = (
            LegacyCredentials.parse(self.service.credentials)
            if self.service.credentials
            else None
        )
        client = RaopClient(cast(RtspSession, session), context, credentials)
        try:
            client.listener = self.listener
            await client.initialize(self.service.properties)

            # After initialize has been called, all the audio properties will be
            # initialized and can be used in the miniaudio wrapper
            audio_file = await MiniaudioWrapper.open(
                filename,
                context.sample_rate,
                context.channels,
                context.bytes_per_channel,
            )

            # Try to load metadata and pass it along if it succeeds
            metadata: AudioMetadata = EMPTY_METADATA
            try:
                metadata = await get_metadata(filename)
            except Exception as ex:
                _LOGGER.warning("Failed to extract metadata from %s: %s", filename, ex)

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
                remapped = map_range(initial_volume, -30.0, 0.0, 0.0, 100.0)
                await self.audio.set_volume(remapped)
            else:
                remapped = map_range(self.audio.volume, 0.0, 100.0, -30.0, 0.0)
                await session.set_parameter("volume", str(remapped))

            await client.send_audio(audio_file, metadata)
        finally:
            if client:
                client.close()
            connection.close()


def setup(
    loop: asyncio.AbstractEventLoop,
    config: conf.AppleTV,
    interfaces: Dict[Any, Relayer],
    device_listener: StateProducer,
    session_manager: ClientSessionManager,
) -> Optional[
    Tuple[Callable[[], Awaitable[None]], Callable[[], None], Set[FeatureName]]
]:
    """Set up a new RAOP service."""
    service = config.get_service(Protocol.RAOP)
    assert service is not None

    state_manager = RaopStateManager()
    metadata = RaopMetadata(state_manager)
    push_updater = RaopPushUpdater(metadata, loop)

    class RaopStateListener(RaopListener):
        """Listener for RAOP state changes."""

        def playing(self, playback_info: PlaybackInfo) -> None:
            """Media started playing with metadata."""
            state_manager.playback_info = playback_info
            self._trigger()

        def stopped(self) -> None:
            """Media stopped playing."""
            state_manager.playback_info = None
            self._trigger()

        @staticmethod
        def _trigger():
            """Trigger push update."""
            if push_updater.active:
                asyncio.ensure_future(push_updater.state_updated(), loop=loop)

    service = cast(conf.RaopService, service)

    raop_listener = RaopStateListener()
    raop_audio = RaopAudio()

    interfaces[Stream].register(
        RaopStream(str(config.address), service, raop_listener, raop_audio),
        Protocol.RAOP,
    )
    interfaces[Features].register(RaopFeatures(state_manager), Protocol.RAOP)
    interfaces[PushUpdater].register(push_updater, Protocol.RAOP)
    interfaces[Metadata].register(metadata, Protocol.RAOP)
    interfaces[Audio].register(raop_audio, Protocol.RAOP)

    async def _connect() -> None:
        pass

    def _close() -> None:
        pass

    return (
        _connect,
        _close,
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
            ]
        ),
    )
