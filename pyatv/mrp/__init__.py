"""Implementation of the MediaRemoteTV Protocol used by ATV4 and later."""

import math
import logging
import asyncio
import datetime
from typing import Dict, List, Optional, Tuple

from pyatv import conf, exceptions
from pyatv.const import (
    Protocol,
    MediaType,
    DeviceState,
    RepeatState,
    ShuffleState,
    PowerState,
    FeatureState,
    FeatureName,
    InputAction,
)
from pyatv.support.cache import Cache
from pyatv.mrp import messages, protobuf
from pyatv.mrp.srp import SRPAuthHandler
from pyatv.mrp.connection import MrpConnection
from pyatv.mrp.protocol import MrpProtocol
from pyatv.mrp.protobuf import CommandInfo_pb2, PlaybackState
from pyatv.mrp.protobuf import ContentItemMetadata as cim
from pyatv.mrp.player_state import PlayerStateManager, PlayerState
from pyatv.interface import (
    AppleTV,
    DeviceInfo,
    Stream,
    RemoteControl,
    App,
    Metadata,
    Playing,
    PushUpdater,
    ArtworkInfo,
    Power,
    Features,
    FeatureInfo,
)
from pyatv.support import deprecated
from pyatv.support.net import ClientSessionManager


_LOGGER = logging.getLogger(__name__)

# Source: https://github.com/Daij-Djan/DDHidLib/blob/master/usb_hid_usages.txt
_KEY_LOOKUP = {
    # name: [usage_page, usage]
    "up": (1, 0x8C),
    "down": (1, 0x8D),
    "left": (1, 0x8B),
    "right": (1, 0x8A),
    "stop": (12, 0xB7),
    "next": (12, 0xB5),
    "previous": (12, 0xB6),
    "select": (1, 0x89),
    "menu": (1, 0x86),
    "topmenu": (12, 0x60),
    "home": (12, 0x40),
    "suspend": (1, 0x82),
    "wakeup": (1, 0x83),
    "volume_up": (12, 0xE9),
    "volume_down": (12, 0xEA),
    # 'mic': (12, 0x04),  # Siri
}  # Dict[str, Tuple[int, int]]


_FEATURES_SUPPORTED = [
    FeatureName.Down,
    FeatureName.Home,
    FeatureName.HomeHold,
    FeatureName.Left,
    FeatureName.Menu,
    FeatureName.Right,
    FeatureName.Select,
    FeatureName.TopMenu,
    FeatureName.Up,
    FeatureName.TurnOn,
    FeatureName.TurnOff,
    FeatureName.PowerState,
]  # type: List[FeatureName]

_FEATURE_COMMAND_MAP = {
    FeatureName.Next: CommandInfo_pb2.NextTrack,
    FeatureName.Pause: CommandInfo_pb2.Pause,
    FeatureName.Play: CommandInfo_pb2.Play,
    FeatureName.PlayPause: CommandInfo_pb2.TogglePlayPause,
    FeatureName.Previous: CommandInfo_pb2.PreviousTrack,
    FeatureName.Stop: CommandInfo_pb2.Stop,
    FeatureName.SetPosition: CommandInfo_pb2.SeekToPlaybackPosition,
    FeatureName.SetRepeat: CommandInfo_pb2.ChangeRepeatMode,
    FeatureName.SetShuffle: CommandInfo_pb2.ChangeShuffleMode,
    FeatureName.Shuffle: CommandInfo_pb2.ChangeShuffleMode,
    FeatureName.Repeat: CommandInfo_pb2.ChangeRepeatMode,
    FeatureName.SkipForward: CommandInfo_pb2.SkipForward,
    FeatureName.SkipBackward: CommandInfo_pb2.SkipBackward,
}

# Features that are considered available if corresponding
_FIELD_FEATURES = {
    FeatureName.Title: "title",
    FeatureName.Artist: "trackArtistName",
    FeatureName.Album: "albumName",
    FeatureName.Genre: "genre",
    FeatureName.TotalTime: "duration",
    FeatureName.Position: "elapsedTimeTimestamp",
}  # type: Dict[FeatureName, str]

DELAY_BETWEEN_COMMANDS = 0.1


def _cocoa_to_timestamp(time):
    delta = datetime.datetime(2001, 1, 1) - datetime.datetime(1970, 1, 1)
    time_seconds = (datetime.timedelta(seconds=time) + delta).total_seconds()
    return datetime.datetime.fromtimestamp(time_seconds)


def build_playing_instance(state: PlayerState) -> Playing:
    """Build a Playing instance from play state."""

    def media_type() -> MediaType:
        """Type of media is currently playing, e.g. video, music."""
        if state.metadata:
            media_type = state.metadata.mediaType
            if media_type == cim.Audio:
                return MediaType.Music
            if media_type == cim.Video:
                return MediaType.Video

        return MediaType.Unknown

    def device_state() -> DeviceState:
        """Device state, e.g. playing or paused."""
        return {
            None: DeviceState.Idle,
            PlaybackState.Playing: DeviceState.Playing,
            PlaybackState.Paused: DeviceState.Paused,
            PlaybackState.Stopped: DeviceState.Stopped,
            PlaybackState.Interrupted: DeviceState.Loading,
            PlaybackState.Seeking: DeviceState.Seeking,
        }.get(state.playback_state, DeviceState.Paused)

    def title() -> Optional[str]:
        """Title of the current media, e.g. movie or song name."""
        return state.metadata_field("title")

    def artist() -> Optional[str]:
        """Artist of the currently playing song."""
        return state.metadata_field("trackArtistName")

    def album() -> Optional[str]:
        """Album of the currently playing song."""
        return state.metadata_field("albumName")

    def genre() -> Optional[str]:
        """Genre of the currently playing song."""
        return state.metadata_field("genre")

    def total_time() -> Optional[int]:
        """Total play time in seconds."""
        duration = state.metadata_field("duration")
        if duration is None or math.isnan(duration):
            return None
        return int(duration)

    def position() -> Optional[int]:
        """Position in the playing media (seconds)."""
        elapsed_timestamp = state.metadata_field("elapsedTimeTimestamp")

        # If we don't have reference time, we can't do anything
        if not elapsed_timestamp:
            return None

        elapsed_time: int = state.metadata_field("elapsedTime") or 0
        diff = (
            datetime.datetime.now() - _cocoa_to_timestamp(elapsed_timestamp)
        ).total_seconds()

        if device_state() == DeviceState.Playing:
            return int(elapsed_time + diff)
        return int(elapsed_time)

    def shuffle() -> ShuffleState:
        """If shuffle is enabled or not."""
        info = state.command_info(CommandInfo_pb2.ChangeShuffleMode)
        if info is None:
            return ShuffleState.Off
        if info.shuffleMode == protobuf.ShuffleMode.Off:
            return ShuffleState.Off
        if info.shuffleMode == protobuf.ShuffleMode.Albums:
            return ShuffleState.Albums

        return ShuffleState.Songs

    def repeat() -> RepeatState:
        """Repeat mode."""
        info = state.command_info(CommandInfo_pb2.ChangeRepeatMode)
        if info is None:
            return RepeatState.Off
        if info.repeatMode == protobuf.RepeatMode.One:
            return RepeatState.Track
        if info.repeatMode == protobuf.RepeatMode.All:
            return RepeatState.All

        return RepeatState.Off

    def hash() -> str:
        """Create a unique hash for what is currently playing."""
        return state.item_identifier

    return Playing(
        media_type=media_type(),
        device_state=device_state(),
        title=title(),
        artist=artist(),
        album=album(),
        genre=genre(),
        total_time=total_time(),
        position=position(),
        shuffle=shuffle(),
        repeat=repeat(),
        hash=hash(),
    )


# pylint: disable=too-many-public-methods
class MrpRemoteControl(RemoteControl):
    """Implementation of API for controlling an Apple TV."""

    def __init__(
        self,
        loop: asyncio.AbstractEventLoop,
        psm: PlayerStateManager,
        protocol: MrpProtocol,
    ) -> None:
        """Initialize a new MrpRemoteControl."""
        self.loop = loop
        self.psm = psm
        self.protocol = protocol

    async def _press_key(self, key: str, action: InputAction) -> None:
        async def _do_press(keycode: Tuple[int, int], hold: bool):
            await self.protocol.send(
                messages.send_hid_event(keycode[0], keycode[1], True)
            )

            if hold:
                # Hardcoded hold time for one second
                await asyncio.sleep(1)

            await self.protocol.send(
                messages.send_hid_event(keycode[0], keycode[1], False)
            )

        keycode = _KEY_LOOKUP.get(key)
        if not keycode:
            raise Exception(f"unsupported key: {key}")

        if action == InputAction.SingleTap:
            await _do_press(keycode, False)
        elif action == InputAction.DoubleTap:
            await _do_press(keycode, False)
            await _do_press(keycode, False)
        elif action == InputAction.Hold:
            await _do_press(keycode, True)
        else:
            raise Exception(f"unsupported input action: {action}")

    async def _send_command(self, command, **kwargs):
        resp = await self.protocol.send_and_receive(messages.command(command, **kwargs))
        inner = resp.inner()

        if inner.sendError == protobuf.SendError.NoError:
            return

        raise exceptions.CommandError(
            f"{CommandInfo_pb2.Command.Name(command)} failed: "
            f"SendError={protobuf.SendError.Enum.Name(inner.sendError)}, "
            "HandlerReturnStatus="
            f"{protobuf.HandlerReturnStatus.Enum.Name(inner.handlerReturnStatus)}"
        )

    async def up(self, action: InputAction = InputAction.SingleTap) -> None:
        """Press key up."""
        await self._press_key("up", action)

    async def down(self, action: InputAction = InputAction.SingleTap) -> None:
        """Press key down."""
        await self._press_key("down", action)

    async def left(self, action: InputAction = InputAction.SingleTap) -> None:
        """Press key left."""
        await self._press_key("left", action)

    async def right(self, action: InputAction = InputAction.SingleTap) -> None:
        """Press key right."""
        await self._press_key("right", action)

    async def play(self) -> None:
        """Press key play."""
        await self._send_command(CommandInfo_pb2.Play)

    async def play_pause(self) -> None:
        """Toggle between play and pause."""
        # Cannot use the feature interface here since it emulates the feature state
        cmd = self.psm.playing.command_info(CommandInfo_pb2.TogglePlayPause)
        if cmd and cmd.enabled:
            await self._send_command(CommandInfo_pb2.TogglePlayPause)
        else:
            state = self.psm.playing.playback_state
            if state == PlaybackState.Playing:
                await self.pause()
            elif state == PlaybackState.Paused:
                await self.play()

    async def pause(self) -> None:
        """Press key play."""
        await self._send_command(CommandInfo_pb2.Pause)

    async def stop(self) -> None:
        """Press key stop."""
        await self._send_command(CommandInfo_pb2.Stop)

    async def next(self) -> None:
        """Press key next."""
        await self._send_command(CommandInfo_pb2.NextTrack)

    async def previous(self) -> None:
        """Press key previous."""
        await self._send_command(CommandInfo_pb2.PreviousTrack)

    async def select(self, action: InputAction = InputAction.SingleTap) -> None:
        """Press key select."""
        await self._press_key("select", action)

    async def menu(self, action: InputAction = InputAction.SingleTap) -> None:
        """Press key menu."""
        await self._press_key("menu", action)

    async def volume_up(self) -> None:
        """Press key volume up."""
        await self._press_key("volume_up", InputAction.SingleTap)

    async def volume_down(self) -> None:
        """Press key volume down."""
        await self._press_key("volume_down", InputAction.SingleTap)

    async def home(self, action: InputAction = InputAction.SingleTap) -> None:
        """Press key home."""
        await self._press_key("home", action)

    @deprecated
    async def home_hold(self) -> None:
        """Hold key home."""
        await self._press_key("home", InputAction.Hold)

    async def top_menu(self) -> None:
        """Go to main menu (long press menu)."""
        await self._press_key("topmenu", InputAction.SingleTap)

    @deprecated
    async def suspend(self) -> None:
        """Suspend the device."""
        await self._press_key("suspend", InputAction.SingleTap)

    @deprecated
    async def wakeup(self) -> None:
        """Wake up the device."""
        await self._press_key("wakeup", InputAction.SingleTap)

    async def skip_forward(self) -> None:
        """Skip forward a time interval.

        Skip interval is typically 15-30s, but is decided by the app.
        """
        await self._skip_command(CommandInfo_pb2.SkipForward)

    async def skip_backward(self) -> None:
        """Skip backwards a time interval.

        Skip interval is typically 15-30s, but is decided by the app.
        """
        await self._skip_command(CommandInfo_pb2.SkipBackward)

    async def _skip_command(self, command) -> None:
        info = self.psm.playing.command_info(command)

        # Pick the first preferred interval for simplicity
        if info and info.preferredIntervals:
            skip_interval = info.preferredIntervals[0]
        else:
            skip_interval = 15  # Default value

        await self._send_command(command, skipInterval=skip_interval)

    async def set_position(self, pos: int) -> None:
        """Seek in the current playing media."""
        await self.protocol.send_and_receive(messages.seek_to_position(pos))

    async def set_shuffle(self, shuffle_state: ShuffleState) -> None:
        """Change shuffle mode to on or off."""
        await self.protocol.send_and_receive(messages.shuffle(shuffle_state))

    async def set_repeat(self, repeat_state: RepeatState) -> None:
        """Change repeat state."""
        await self.protocol.send_and_receive(messages.repeat(repeat_state))


class MrpMetadata(Metadata):
    """Implementation of API for retrieving metadata."""

    def __init__(self, protocol, psm, identifier):
        """Initialize a new MrpPlaying."""
        super().__init__(identifier)
        self.protocol = protocol
        self.psm = psm
        self.artwork_cache = Cache(limit=4)

    async def artwork(self, width=512, height=None) -> Optional[ArtworkInfo]:
        """Return artwork for what is currently playing (or None).

        The parameters "width" and "height" makes it possible to request artwork of a
        specific size. This is just a request, the device might impose restrictions and
        return artwork of a different size. Set both parameters to None to request
        default size. Set one of them and let the other one be None to keep original
        aspect ratio.
        """
        identifier = self.artwork_id
        if not identifier:
            _LOGGER.debug("No artwork available")
            return None

        if identifier in self.artwork_cache:
            _LOGGER.debug("Retrieved artwork %s from cache", identifier)
            return self.artwork_cache.get(identifier)

        artwork = await self._fetch_artwork(width or 0, height or -1)
        if artwork:
            self.artwork_cache.put(identifier, artwork)
            return artwork

        return None

    async def _fetch_artwork(self, width, height):
        playing = self.psm.playing
        resp = await self.psm.protocol.send_and_receive(
            messages.playback_queue_request(playing.location, width, height)
        )
        if not resp.HasField("type"):
            return None

        item = resp.inner().playbackQueue.contentItems[playing.location]
        return ArtworkInfo(
            bytes=item.artworkData,
            mimetype=playing.metadata.artworkMIMEType,
            width=item.artworkDataWidth,
            height=item.artworkDataHeight,
        )

    @property
    def artwork_id(self):
        """Return a unique identifier for current artwork."""
        metadata = self.psm.playing.metadata
        if metadata and metadata.artworkAvailable:
            if metadata.HasField("artworkIdentifier"):
                return metadata.artworkIdentifier
            if metadata.HasField("contentIdentifier"):
                return metadata.contentIdentifier
            return self.psm.playing.item_identifier
        return None

    async def playing(self) -> Playing:
        """Return what is currently playing."""
        return build_playing_instance(self.psm.playing)

    @property
    def app(self) -> Optional[App]:
        """Return information about running app."""
        client = self.psm.client
        if client:
            return App(client.display_name, client.bundle_identifier)
        return None


class MrpPower(Power):
    """Implementation of API for retrieving a power state from an Apple TV."""

    def __init__(
        self,
        loop: asyncio.AbstractEventLoop,
        protocol: MrpProtocol,
        remote: MrpRemoteControl,
    ) -> None:
        """Initialize a new MrpPower instance."""
        super().__init__()
        self.loop = loop
        self.protocol = protocol
        self.remote = remote
        self.device_info = None
        self._waiters: Dict[PowerState, asyncio.Event] = {}

        self.protocol.add_listener(
            self._update_power_state, protobuf.DEVICE_INFO_UPDATE_MESSAGE
        )

    def _get_current_power_state(self) -> PowerState:
        latest_device_info = self.device_info or self.protocol.device_info
        return self._get_power_state(latest_device_info)

    @property
    def power_state(self) -> PowerState:
        """Return device power state."""
        currect_power_state = self._get_current_power_state()
        return currect_power_state

    async def turn_on(self, await_new_state: bool = False) -> None:
        """Turn device on."""
        await self.protocol.send(messages.wake_device())

        if await_new_state and self.power_state != PowerState.On:
            await self._waiters.setdefault(PowerState.On, asyncio.Event()).wait()

    async def turn_off(self, await_new_state: bool = False) -> None:
        """Turn device off."""
        await self.remote.home(InputAction.Hold)
        await asyncio.sleep(DELAY_BETWEEN_COMMANDS)
        await self.remote.select()

        if await_new_state and self.power_state != PowerState.Off:
            await self._waiters.setdefault(PowerState.Off, asyncio.Event()).wait()

    async def _update_power_state(self, message, _):
        old_state = self.power_state
        new_state = self._get_power_state(message)
        self.device_info = message

        if new_state != old_state:
            _LOGGER.debug("Power state changed from %s to %s", old_state, new_state)
            self.loop.call_soon(self.listener.powerstate_update, old_state, new_state)

        if new_state in self._waiters:
            self._waiters[new_state].set()
            del self._waiters[new_state]

    @staticmethod
    def _get_power_state(device_info) -> PowerState:
        logical_device_count = device_info.inner().logicalDeviceCount
        if logical_device_count >= 1:
            return PowerState.On
        if logical_device_count == 0:
            return PowerState.Off
        return PowerState.Unknown


class MrpPushUpdater(PushUpdater):
    """Implementation of API for handling push update from an Apple TV."""

    def __init__(self, loop, metadata, psm):
        """Initialize a new MrpPushUpdater instance."""
        super().__init__(loop)
        self.metadata = metadata
        self.psm = psm

    @property
    def active(self):
        """Return if push updater has been started."""
        return self.psm.listener == self

    def start(self, initial_delay=0):
        """Wait for push updates from device.

        Will throw NoAsyncListenerError if no listener has been set.
        """
        if self.listener is None:
            raise exceptions.NoAsyncListenerError()
        if self.active:
            return

        self.psm.listener = self
        asyncio.ensure_future(self.state_updated(), loop=self.loop)

    def stop(self):
        """No longer forward updates to listener."""
        self.psm.listener = None

    async def state_updated(self):
        """State was updated for active player."""
        try:
            playstatus = await self.metadata.playing()
            self.post_update(playstatus)
        except Exception as ex:  # pylint: disable=broad-except
            _LOGGER.debug("Playstatus error occurred: %s", ex)
            self.loop.call_soon(self.listener.playstatus_error, self, ex)


class MrpFeatures(Features):
    """Implementation of API for supported feature functionality."""

    def __init__(self, config: conf.AppleTV, psm: PlayerStateManager):
        """Initialize a new MrpFeatures instance."""
        self.config = config
        self.psm = psm

    def get_feature(self, feature: FeatureName) -> FeatureInfo:
        """Return current state of a feature."""
        if feature in _FEATURES_SUPPORTED:
            return FeatureInfo(state=FeatureState.Available)
        if feature == FeatureName.Artwork:
            metadata = self.psm.playing.metadata
            if metadata and metadata.artworkAvailable:
                return FeatureInfo(state=FeatureState.Available)
            return FeatureInfo(state=FeatureState.Unavailable)
        if feature == FeatureName.PlayUrl:
            if self.config.get_service(Protocol.AirPlay) is not None:
                return FeatureInfo(state=FeatureState.Available)

        field_name = _FIELD_FEATURES.get(feature)
        if field_name:
            available = self.psm.playing.metadata_field(field_name) is not None
            return FeatureInfo(
                state=FeatureState.Available if available else FeatureState.Unavailable
            )

        # Special case for PlayPause emulation. Based on the behavior in the Youtube
        # app, only the "opposite" feature to current state is available. E.g. if
        # something is playing, then pause will be available but not play. So take that
        # into consideration here.
        if feature == FeatureName.PlayPause:
            playback_state = self.psm.playing.playback_state
            if playback_state == PlaybackState.Playing and self.in_state(
                FeatureState.Available, FeatureName.Pause
            ):
                return FeatureInfo(state=FeatureState.Available)
            if playback_state == PlaybackState.Paused and self.in_state(
                FeatureState.Available, FeatureName.Play
            ):
                return FeatureInfo(state=FeatureState.Available)

        cmd_id = _FEATURE_COMMAND_MAP.get(feature)
        if cmd_id:
            cmd = self.psm.playing.command_info(cmd_id)
            if cmd and cmd.enabled:
                return FeatureInfo(state=FeatureState.Available)
            return FeatureInfo(state=FeatureState.Unavailable)

        if feature == FeatureName.App:
            if self.psm.client:
                return FeatureInfo(state=FeatureState.Available)
            return FeatureInfo(state=FeatureState.Unavailable)

        if feature in [FeatureName.VolumeDown, FeatureName.VolumeUp]:
            if self.psm.volume_controls_available:
                return FeatureInfo(state=FeatureState.Available)
            return FeatureInfo(state=FeatureState.Unavailable)

        return FeatureInfo(state=FeatureState.Unsupported)


class MrpAppleTV(AppleTV):
    """Implementation of API support for Apple TV."""

    # This is a container class so it's OK with many attributes
    # pylint: disable=too-many-instance-attributes
    def __init__(
        self,
        loop: asyncio.AbstractEventLoop,
        session_manager: ClientSessionManager,
        config: conf.AppleTV,
        airplay: Stream,
    ) -> None:
        """Initialize a new Apple TV."""
        super().__init__()

        self._session_manager = session_manager
        self._config = config
        self._mrp_service = config.get_service(Protocol.MRP)
        assert self._mrp_service is not None

        self._connection = MrpConnection(
            config.address, self._mrp_service.port, loop, atv=self
        )
        self._srp = SRPAuthHandler()
        self._protocol = MrpProtocol(self._connection, self._srp, self._mrp_service)
        self._psm = PlayerStateManager(self._protocol)

        self._mrp_remote = MrpRemoteControl(loop, self._psm, self._protocol)
        self._mrp_metadata = MrpMetadata(self._protocol, self._psm, config.identifier)
        self._mrp_power = MrpPower(loop, self._protocol, self._mrp_remote)
        self._mrp_push_updater = MrpPushUpdater(loop, self._mrp_metadata, self._psm)
        self._mrp_features = MrpFeatures(self._config, self._psm)
        self._airplay = airplay

    async def connect(self) -> None:
        """Initiate connection to device.

        No need to call it yourself, it's done automatically.
        """
        await self._protocol.start()

    def close(self) -> None:
        """Close connection and release allocated resources."""
        asyncio.ensure_future(self._session_manager.close())
        self._airplay.close()
        self.push_updater.stop()
        self._protocol.stop()

    @property
    def device_info(self) -> DeviceInfo:
        """Return API for device information."""
        return self._config.device_info

    @property
    def service(self):
        """Return service used to connect to the Apple TV."""
        return self._mrp_service

    @property
    def remote_control(self) -> RemoteControl:
        """Return API for controlling the Apple TV."""
        return self._mrp_remote

    @property
    def metadata(self) -> Metadata:
        """Return API for retrieving metadata from Apple TV."""
        return self._mrp_metadata

    @property
    def push_updater(self) -> PushUpdater:
        """Return API for handling push update from the Apple TV."""
        return self._mrp_push_updater

    @property
    def stream(self) -> Stream:
        """Return API for streaming media."""
        return self._airplay

    @property
    def power(self) -> Power:
        """Return API for streaming media."""
        return self._mrp_power

    @property
    def features(self) -> Features:
        """Return features interface."""
        return self._mrp_features
