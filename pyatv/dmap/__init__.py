"""Implementation of the DMAP protocol used by ATV 1, 2 and 3."""

import logging
import asyncio
import weakref
from typing import Dict, List, Optional

from aiohttp.client_exceptions import ClientError

from pyatv import conf, exceptions
from pyatv.support import net
from pyatv.support.cache import Cache
from pyatv.const import (
    Protocol,
    MediaType,
    RepeatState,
    ShuffleState,
    PowerState,
    FeatureState,
    FeatureName,
    InputAction,
)
from pyatv.dmap import daap, parser, tags
from pyatv.dmap.daap import DaapRequester
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

# Skip forward/backwards isn't supported by the protocol so it is simulated by seeking
# this many seconds forward/backwards in time
_DEFAULT_SKIP_TIME = 10

_PSU_CMD = "ctrl-int/1/playstatusupdate?[AUTH]&revision-number={0}"
_ARTWORK_CMD = "ctrl-int/1/nowplayingartwork?mw={width}&mh={height}&[AUTH]"
_CTRL_PROMPT_CMD = "ctrl-int/1/controlpromptentry?[AUTH]&prompt-id=0"

# Features that are always considered to be available
_AVAILABLE_FEATURES = [
    FeatureName.Down,
    FeatureName.Left,
    FeatureName.Menu,
    FeatureName.Right,
    FeatureName.Select,
    FeatureName.TopMenu,
    FeatureName.Up,
]  # type: List[FeatureName]

# Features that are supported by the device but we don't now if available
_UNKNOWN_FEATURES = [
    FeatureName.Artwork,
    FeatureName.Next,
    FeatureName.Pause,
    FeatureName.Play,
    FeatureName.PlayPause,
    FeatureName.Previous,
    FeatureName.SetPosition,
    FeatureName.SetRepeat,
    FeatureName.SetShuffle,
    FeatureName.Stop,
    FeatureName.SkipForward,
    FeatureName.SkipBackward,
]  # type: List[FeatureName]

# Features that are considered available if corresponding field is present
_FIELD_FEATURES = {
    FeatureName.Title: ("cmst", "caps"),
    FeatureName.Artist: ("cmst", "cann"),
    FeatureName.Album: ("cmst", "canl"),
    FeatureName.Genre: ("cmst", "cang"),
    FeatureName.TotalTime: ("cmst", "cast"),
    FeatureName.Position: ("cmst", "cant"),
    FeatureName.Shuffle: ("cmst", "cash"),
    FeatureName.Repeat: ("cmst", "carp"),
}  # type: Dict[FeatureName, tuple]


class BaseDmapAppleTV:
    """Common protocol logic used to interact with an Apple TV."""

    def __init__(self, requester):
        """Initialize a new Apple TV base implementation."""
        self.daap = requester
        self.playstatus_revision = 0
        self.latest_playing = None
        self.latest_hash = None

    async def playstatus(self, use_revision=False, timeout=None):
        """Request raw data about what is currently playing.

        If use_revision=True, this command will "block" until playstatus
        changes on the device.

        Must be logged in.
        """
        cmd_url = _PSU_CMD.format(self.playstatus_revision if use_revision else 0)
        resp = await self.daap.get(cmd_url, timeout=timeout)
        self.playstatus_revision = parser.first(resp, "cmst", "cmsr")
        self.latest_playing = DmapPlaying(resp)
        self.latest_hash = self.latest_playing.hash
        return self.latest_playing

    async def artwork(self, width, height) -> Optional[ArtworkInfo]:
        """Return artwork for what is currently playing (or None)."""
        url = _ARTWORK_CMD.format(width=width or 0, height=height or 0)
        art = await self.daap.get(url, daap_data=False)
        return art if art != b"" else None

    def ctrl_int_cmd(self, cmd):
        """Perform a "ctrl-int" command."""
        cmd_url = "ctrl-int/1/{}?[AUTH]&prompt-id=0".format(cmd)
        return self.daap.post(cmd_url)

    def controlprompt_cmd(self, cmd):
        """Perform a "controlpromptentry" command."""
        data = tags.string_tag("cmbe", cmd) + tags.uint8_tag("cmcc", 0)
        return self.daap.post(_CTRL_PROMPT_CMD, data=data)

    def controlprompt_data(self, data):
        """Perform a "controlpromptentry" command."""
        return self.daap.post(_CTRL_PROMPT_CMD, data=data)

    def set_property(self, prop, value):
        """Change value of a DAAP property, e.g. volume or media position."""
        cmd_url = "ctrl-int/1/setproperty?{}={}&[AUTH]".format(prop, value)
        return self.daap.post(cmd_url)


# pylint: disable=too-many-public-methods
class DmapRemoteControl(RemoteControl):
    """Implementation of API for controlling an Apple TV."""

    def __init__(self, apple_tv) -> None:
        """Initialize remote control instance."""
        super().__init__()
        self.apple_tv = apple_tv

    async def up(self, action: InputAction = InputAction.SingleTap) -> None:
        """Press key up."""
        await self._send_commands(
            self._move("Down", 0, 20, 275),
            self._move("Move", 1, 20, 270),
            self._move("Move", 2, 20, 265),
            self._move("Move", 3, 20, 260),
            self._move("Move", 4, 20, 255),
            self._move("Move", 5, 20, 250),
            self._move("Up", 6, 20, 250),
        )

    async def down(self, action: InputAction = InputAction.SingleTap) -> None:
        """Press key down."""
        await self._send_commands(
            self._move("Down", 0, 20, 250),
            self._move("Move", 1, 20, 255),
            self._move("Move", 2, 20, 260),
            self._move("Move", 3, 20, 265),
            self._move("Move", 4, 20, 270),
            self._move("Move", 5, 20, 275),
            self._move("Up", 6, 20, 275),
        )

    async def left(self, action: InputAction = InputAction.SingleTap) -> None:
        """Press key left."""
        await self._send_commands(
            self._move("Down", 0, 75, 100),
            self._move("Move", 1, 70, 100),
            self._move("Move", 3, 65, 100),
            self._move("Move", 4, 60, 100),
            self._move("Move", 5, 55, 100),
            self._move("Move", 6, 50, 100),
            self._move("Up", 7, 50, 100),
        )

    async def right(self, action: InputAction = InputAction.SingleTap) -> None:
        """Press key right."""
        await self._send_commands(
            self._move("Down", 0, 50, 100),
            self._move("Move", 1, 55, 100),
            self._move("Move", 3, 60, 100),
            self._move("Move", 4, 65, 100),
            self._move("Move", 5, 70, 100),
            self._move("Move", 6, 75, 100),
            self._move("Up", 7, 75, 100),
        )

    @staticmethod
    def _move(direction, time, point1, point2):
        data = "touch{0}&time={1}&point={2},{3}".format(direction, time, point1, point2)
        return tags.uint8_tag("cmcc", 0x30) + tags.string_tag("cmbe", data)

    async def _send_commands(self, *cmds) -> None:
        for cmd in cmds:
            await self.apple_tv.controlprompt_data(cmd)

    async def play(self) -> None:
        """Press key play."""
        await self.apple_tv.ctrl_int_cmd("play")

    async def play_pause(self) -> None:
        """Toggle between play and pause."""
        await self.apple_tv.ctrl_int_cmd("playpause")

    async def pause(self) -> None:
        """Press key pause."""
        await self.apple_tv.ctrl_int_cmd("pause")

    async def stop(self) -> None:
        """Press key stop."""
        await self.apple_tv.ctrl_int_cmd("stop")

    async def next(self) -> None:
        """Press key next."""
        await self.apple_tv.ctrl_int_cmd("nextitem")

    async def previous(self) -> None:
        """Press key previous."""
        await self.apple_tv.ctrl_int_cmd("previtem")

    async def select(self, action: InputAction = InputAction.SingleTap) -> None:
        """Press key select."""
        await self.apple_tv.controlprompt_cmd("select")

    async def menu(self, action: InputAction = InputAction.SingleTap) -> None:
        """Press key menu."""
        await self.apple_tv.controlprompt_cmd("menu")

    async def top_menu(self) -> None:
        """Press key topmenu."""
        await self.apple_tv.controlprompt_cmd("topmenu")

    async def volume_up(self) -> None:
        """Press key volume up."""
        await self.apple_tv.ctrl_int_cmd("volumeup")

    async def volume_down(self) -> None:
        """Press key volume down."""
        await self.apple_tv.ctrl_int_cmd("volumedown")

    async def home(self, action: InputAction = InputAction.SingleTap) -> None:
        """Press key home."""
        # DMAP support unknown
        raise exceptions.NotSupportedError()

    @deprecated
    async def home_hold(self) -> None:
        """Hold key home."""
        # DMAP support unknown
        raise exceptions.NotSupportedError()

    @deprecated
    async def suspend(self) -> None:
        """Suspend the device."""
        # Not supported by DMAP
        raise exceptions.NotSupportedError()

    @deprecated
    async def wakeup(self) -> None:
        """Wake up the device."""
        raise exceptions.NotSupportedError()

    async def skip_forward(self) -> None:
        """Skip forward a time interval.

        Skip interval is typically 15-30s, but is decided by the app.
        """
        current_position = (await self.apple_tv.playstatus()).position
        if current_position:
            await self.set_position(current_position + _DEFAULT_SKIP_TIME)

    async def skip_backward(self) -> None:
        """Skip backwards a time interval.

        Skip interval is typically 15-30s, but is decided by the app.
        """
        current_position = (await self.apple_tv.playstatus()).position
        if current_position:
            await self.set_position(current_position - _DEFAULT_SKIP_TIME)

    async def set_position(self, pos: int) -> None:
        """Seek in the current playing media."""
        time_in_ms = int(pos) * 1000
        await self.apple_tv.set_property("dacp.playingtime", time_in_ms)

    async def set_shuffle(self, shuffle_state: ShuffleState) -> None:
        """Change shuffle mode to on or off."""
        state = 0 if shuffle_state == ShuffleState.Off else 1
        await self.apple_tv.set_property("dacp.shufflestate", state)

    async def set_repeat(self, repeat_state: RepeatState) -> None:
        """Change repeat mode."""
        await self.apple_tv.set_property("dacp.repeatstate", repeat_state.value)


class DmapPlaying(Playing):
    """Implementation of API for retrieving what is playing."""

    def __init__(self, playstatus):
        """Initialize playing instance."""
        super().__init__()
        self.playstatus = playstatus

    @property
    def media_type(self):
        """Type of media is currently playing, e.g. video, music."""
        state = parser.first(self.playstatus, "cmst", "caps")
        if not state:
            return MediaType.Unknown

        mediakind = parser.first(self.playstatus, "cmst", "cmmk")
        if mediakind is not None:
            return daap.media_kind(mediakind)

        # Fallback: if artist or album exists we assume music (not present
        # for video)
        if self.artist or self.album:
            return MediaType.Music

        return MediaType.Video

    @property
    def device_state(self):
        """Device state, e.g. playing or paused."""
        state = parser.first(self.playstatus, "cmst", "caps")
        return daap.playstate(state)

    @property
    def title(self):
        """Title of the current media, e.g. movie or song name."""
        return parser.first(self.playstatus, "cmst", "cann")

    @property
    def artist(self):
        """Arist of the currently playing song."""
        return parser.first(self.playstatus, "cmst", "cana")

    @property
    def album(self):
        """Album of the currently playing song."""
        return parser.first(self.playstatus, "cmst", "canl")

    @property
    def genre(self):
        """Genre of the currently playing song."""
        return parser.first(self.playstatus, "cmst", "cang")

    @property
    def total_time(self):
        """Total play time in seconds."""
        return self._get_time_in_seconds("cast")

    @property
    def position(self):
        """Position in the playing media (seconds)."""
        return self.total_time - self._get_time_in_seconds("cant")

    @property
    def shuffle(self):
        """If shuffle is enabled or not."""
        state = parser.first(self.playstatus, "cmst", "cash")
        if state is None or state == 0:
            return ShuffleState.Off

        # DMAP does not support the "albums" state and will always report
        # "songs" if shuffle is active
        return ShuffleState.Songs

    @property
    def repeat(self):
        """Repeat mode."""
        state = parser.first(self.playstatus, "cmst", "carp")
        if state is None:
            return RepeatState.Off
        return RepeatState(state)

    def _get_time_in_seconds(self, tag):
        time = parser.first(self.playstatus, "cmst", tag)
        return daap.ms_to_s(time)


class DmapMetadata(Metadata):
    """Implementation of API for retrieving metadata from an Apple TV."""

    def __init__(self, identifier, apple_tv):
        """Initialize metadata instance."""
        super().__init__(identifier)
        self.apple_tv = apple_tv
        self.artwork_cache = Cache(limit=4)

    async def artwork(self, width=512, height=None) -> Optional[ArtworkInfo]:
        """Return artwork for what is currently playing (or None).

        The parameters "width" and "height" makes it possible to request artwork of a
        specific size. This is just a request, the device might impose restrictions and
        return artwork of a different size. Set both parameters to None to request
        default size. Set one of them and let the other one be None to keep original
        aspect ratio.
        """
        # Having to fetch "playing" here is not ideal, but an identifier is
        # needed and we cannot trust any previous identifiers. So we have to do
        # this until a better solution comes along.
        playing = await self.playing()
        identifier = playing.hash
        if identifier in self.artwork_cache:
            _LOGGER.debug("Retrieved artwork %s from cache", identifier)
            return self.artwork_cache.get(identifier)

        _LOGGER.debug("Fetching artwork")
        artwork = await self.apple_tv.artwork(width, height)
        if artwork:
            info = ArtworkInfo(bytes=artwork, mimetype="image/png", width=-1, height=-1)
            self.artwork_cache.put(identifier, info)
            return info

        return None

    @property
    def artwork_id(self):
        """Return a unique identifier for current artwork."""
        return self.apple_tv.latest_hash

    async def playing(self):
        """Return current device state."""
        return await self.apple_tv.playstatus()

    @property
    def app(self) -> Optional[App]:
        """Return information about running app."""
        raise exceptions.NotSupportedError()


class DmapPower(Power):
    """Implementation of API for retrieving a power state from an Apple TV."""

    @property
    def power_state(self) -> PowerState:
        """Return device power state."""
        return PowerState.Unknown

    async def turn_on(self, await_new_state: bool = False) -> None:
        """Turn device on."""
        raise exceptions.NotSupportedError()

    async def turn_off(self, await_new_state: bool = False) -> None:
        """Turn device off."""
        raise exceptions.NotSupportedError()


class DmapPushUpdater(PushUpdater):
    """Implementation of API for handling push update from an Apple TV."""

    def __init__(self, loop, apple_tv, listener):
        """Initialize a new DmapPushUpdater instance."""
        super().__init__()
        self._loop = loop
        self._atv = apple_tv
        self._listener = weakref.ref(listener)
        self._future = None
        self._initial_delay = 0

    @property
    def active(self):
        """Return if push updater has been started."""
        return self._future is not None

    def start(self, initial_delay=0):
        """Wait for push updates from device.

        Will throw NoAsyncListenerError if no listener has been set.
        """
        if self.listener is None:
            raise exceptions.NoAsyncListenerError()
        if self.active:
            return

        # Always start with 0 to trigger an immediate response for the
        # first request
        self._atv.playstatus_revision = 0

        # Delay before restarting after an error
        self._initial_delay = initial_delay

        self._future = asyncio.ensure_future(self._poller(), loop=self._loop)

    def stop(self):
        """No longer forward updates to listener."""
        if self._future is not None:
            self._future.cancel()
            self._future = None

    async def _poller(self):
        first_call = True

        while True:
            # Sleep some time before waiting for updates
            if not first_call and self._initial_delay > 0:
                _LOGGER.debug("Initial delay set to %d", self._initial_delay)
                await asyncio.sleep(self._initial_delay, loop=self._loop)
                first_call = False

            try:
                _LOGGER.debug("Waiting for playstatus updates")
                playstatus = await self._atv.playstatus(use_revision=True, timeout=0)

                self._loop.call_soon(self.listener.playstatus_update, self, playstatus)
            except asyncio.CancelledError:
                break

            except ClientError as ex:
                _LOGGER.exception("A communication error happened")
                listener = self._listener()
                if listener:
                    self._loop.call_soon(listener.listener.connection_lost, ex)

                break

            # It is not pretty to disable pylint here, but we must catch _all_
            # exceptions to keep the API.
            except Exception as ex:  # pylint: disable=broad-except
                _LOGGER.debug("Playstatus error occurred: %s", ex)
                self._loop.call_soon(self.listener.playstatus_error, self, ex)

        self._future = None


class DmapFeatures(Features):
    """Implementation of API for supported feature functionality."""

    def __init__(self, config: conf.AppleTV, apple_tv: BaseDmapAppleTV) -> None:
        """Initialize a new DmapFeatures instance."""
        self.config = config
        self.apple_tv = apple_tv

    def get_feature(self, feature: FeatureName) -> FeatureInfo:
        """Return current state of a feature."""
        if feature in _AVAILABLE_FEATURES:
            return FeatureInfo(state=FeatureState.Available)
        if feature in _UNKNOWN_FEATURES:
            return FeatureInfo(state=FeatureState.Unknown)
        if feature in _FIELD_FEATURES:
            return FeatureInfo(state=self._is_available(_FIELD_FEATURES[feature]))
        if feature == FeatureName.VolumeUp:
            return FeatureInfo(state=self._is_available(("cmst", "cavc"), True))
        if feature == FeatureName.VolumeDown:
            return FeatureInfo(state=self._is_available(("cmst", "cavc"), True))
        if feature == FeatureName.PlayUrl:
            if self.config.get_service(Protocol.AirPlay) is not None:
                return FeatureInfo(state=FeatureState.Available)

        return FeatureInfo(state=FeatureState.Unsupported)

    def _is_available(self, field: tuple, expected_value=None) -> FeatureState:
        if self.apple_tv.latest_playing:
            value = parser.first(self.apple_tv.latest_playing.playstatus, *field)
            if value is not None:
                if not expected_value or expected_value == value:
                    return FeatureState.Available
        return FeatureState.Unavailable


class DmapAppleTV(AppleTV):
    """Implementation of API support for Apple TV."""

    # This is a container class so it's OK with many attributes
    # pylint: disable=too-many-instance-attributes
    def __init__(
        self,
        loop,
        session_manager: ClientSessionManager,
        config: conf.AppleTV,
        airplay: Stream,
    ) -> None:
        """Initialize a new Apple TV."""
        super().__init__()
        self._session_manager = session_manager
        self._config = config
        self._dmap_service = config.get_service(Protocol.DMAP)
        assert self._dmap_service is not None
        daap_http = net.HttpSession(
            session_manager.session,
            f"http://{config.address}:{self._dmap_service.port}/",
        )
        self._requester = DaapRequester(daap_http, self._dmap_service.credentials)

        self._apple_tv = BaseDmapAppleTV(self._requester)
        self._dmap_remote = DmapRemoteControl(self._apple_tv)
        self._dmap_metadata = DmapMetadata(config.identifier, self._apple_tv)
        self._dmap_power = DmapPower()
        self._dmap_push_updater = DmapPushUpdater(loop, self._apple_tv, self)
        self._dmap_features = DmapFeatures(config, self._apple_tv)
        self._airplay = airplay

    async def connect(self) -> None:
        """Initiate connection to device.

        No need to call it yourself, it's done automatically.
        """
        await self._requester.login()

    def close(self) -> None:
        """Close connection and release allocated resources."""
        asyncio.ensure_future(self._session_manager.close())
        self._airplay.close()
        self.push_updater.stop()
        self.listener.connection_closed()

    @property
    def device_info(self) -> DeviceInfo:
        """Return API for device information."""
        return self._config.device_info

    @property
    def service(self):
        """Return service used to connect to the Apple TV.."""
        return self._dmap_service

    @property
    def remote_control(self) -> RemoteControl:
        """Return API for controlling the Apple TV."""
        return self._dmap_remote

    @property
    def metadata(self) -> Metadata:
        """Return API for retrieving metadata from Apple TV."""
        return self._dmap_metadata

    @property
    def push_updater(self) -> PushUpdater:
        """Return API for handling push update from the Apple TV."""
        return self._dmap_push_updater

    @property
    def stream(self) -> Stream:
        """Return API for streaming media."""
        return self._airplay

    @property
    def power(self) -> Power:
        """Return API for streaming media."""
        return self._dmap_power

    @property
    def features(self) -> Features:
        """Return features interface."""
        return self._dmap_features
