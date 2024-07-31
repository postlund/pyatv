"""Implementation of the DMAP protocol used by ATV 1, 2 and 3."""

import asyncio
import logging
from typing import Any, Dict, Generator, List, Mapping, Optional, Set, Tuple
import weakref

from aiohttp.client_exceptions import ClientError

from pyatv import exceptions
from pyatv.const import (
    DeviceModel,
    DeviceState,
    FeatureName,
    FeatureState,
    InputAction,
    MediaType,
    OperatingSystem,
    PairingRequirement,
    Protocol,
    RepeatState,
    ShuffleState,
)
from pyatv.core import (
    AbstractPushUpdater,
    Core,
    MutableService,
    ProtocolStateDispatcher,
    SetupData,
    mdns,
)
from pyatv.core.scan import ScanHandlerDeviceInfoName, ScanHandlerReturn
from pyatv.helpers import get_unique_id
from pyatv.interface import (
    ArtworkInfo,
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
)
from pyatv.protocols.dmap import daap, parser, tags
from pyatv.protocols.dmap.daap import DaapRequester
from pyatv.protocols.dmap.pairing import DmapPairingHandler
from pyatv.support.cache import Cache
from pyatv.support.collections import dict_merge
from pyatv.support.http import HttpSession

_LOGGER = logging.getLogger(__name__)

# Skip forward/backwards isn't supported by the protocol so it is simulated by seeking
# this many seconds forward/backwards in time
_DEFAULT_SKIP_TIME = 10

_PSU_CMD = "ctrl-int/1/playstatusupdate?[AUTH]&revision-number={0}"
_ARTWORK_CMD = "ctrl-int/1/nowplayingartwork?mw={width}&mh={height}&[AUTH]"
_CTRL_PROMPT_CMD = "ctrl-int/1/controlpromptentry?[AUTH]&prompt-id=0"

# Features that are always considered to be available
_AVAILABLE_FEATURES: List[FeatureName] = [
    FeatureName.Down,
    FeatureName.Left,
    FeatureName.Menu,
    FeatureName.Right,
    FeatureName.Select,
    FeatureName.TopMenu,
    FeatureName.Up,
]

# Features that are supported by the device but we don't now if available
_UNKNOWN_FEATURES: List[FeatureName] = [
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
]

# Features that are considered available if corresponding field is present
_FIELD_FEATURES: Dict[FeatureName, Tuple[str, str]] = {
    FeatureName.Title: ("cmst", "caps"),
    FeatureName.Artist: ("cmst", "cann"),
    FeatureName.Album: ("cmst", "canl"),
    FeatureName.Genre: ("cmst", "cang"),
    FeatureName.TotalTime: ("cmst", "cast"),
    FeatureName.Position: ("cmst", "cant"),
    FeatureName.Shuffle: ("cmst", "cash"),
    FeatureName.Repeat: ("cmst", "carp"),
}


def build_playing_instance(playstatus) -> Playing:
    """Build a Playing instance from play state."""

    def _get_time_in_seconds(tag) -> int:
        time = parser.first(playstatus, "cmst", tag)
        return daap.ms_to_s(time)

    def media_type() -> MediaType:
        """Type of media is currently playing, e.g. video, music."""
        state = parser.first(playstatus, "cmst", "caps")
        if not state:
            return MediaType.Unknown

        mediakind = parser.first(playstatus, "cmst", "cmmk")
        if mediakind is not None:
            return daap.media_kind(mediakind)

        # Fallback: if artist or album exists we assume music (not present
        # for video)
        if artist() or album():
            return MediaType.Music

        return MediaType.Video

    def device_state() -> DeviceState:
        """Device state, e.g. playing or paused."""
        state = parser.first(playstatus, "cmst", "caps")
        return daap.playstate(state)

    def title() -> Optional[str]:
        """Title of the current media, e.g. movie or song name."""
        return parser.first(playstatus, "cmst", "cann")

    def artist() -> Optional[str]:
        """Arist of the currently playing song."""
        return parser.first(playstatus, "cmst", "cana")

    def album() -> Optional[str]:
        """Album of the currently playing song."""
        return parser.first(playstatus, "cmst", "canl")

    def genre() -> Optional[str]:
        """Genre of the currently playing song."""
        return parser.first(playstatus, "cmst", "cang")

    def total_time() -> Optional[int]:
        """Total play time in seconds."""
        return _get_time_in_seconds("cast")

    def position() -> Optional[int]:
        """Position in the playing media (seconds)."""
        total = total_time()
        remaining_time = _get_time_in_seconds("cant")
        if not total or not remaining_time:
            return None
        return total - remaining_time

    def shuffle() -> Optional[ShuffleState]:
        """If shuffle is enabled or not."""
        state = parser.first(playstatus, "cmst", "cash")
        if state is None or state == 0:
            return ShuffleState.Off

        # DMAP does not support the "albums" state and will always report
        # "songs" if shuffle is active
        return ShuffleState.Songs

    def repeat() -> Optional[RepeatState]:
        """Repeat mode."""
        state = parser.first(playstatus, "cmst", "carp")
        if state is None:
            return RepeatState.Off
        return RepeatState(state)

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
    )


class BaseDmapAppleTV:
    """Common protocol logic used to interact with an Apple TV."""

    def __init__(self, requester):
        """Initialize a new Apple TV base implementation."""
        self.daap = requester
        self.playstatus_revision = 0
        self.latest_playstatus = None
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
        self.latest_playstatus = resp
        self.latest_playing = build_playing_instance(resp)
        self.latest_hash = self.latest_playing.hash
        return self.latest_playing

    async def artwork(
        self, width: Optional[int], height: Optional[int]
    ) -> Optional[ArtworkInfo]:
        """Return artwork for what is currently playing (or None)."""
        url = _ARTWORK_CMD.format(width=width or 0, height=height or 0)
        art = await self.daap.get(url, daap_data=False)
        return art if art != b"" else None

    def ctrl_int_cmd(self, cmd):
        """Perform a "ctrl-int" command."""
        return self.daap.post(f"ctrl-int/1/{cmd}?[AUTH]&prompt-id=0")

    def controlprompt_cmd(self, cmd):
        """Perform a "controlpromptentry" command."""
        data = tags.string_tag("cmbe", cmd) + tags.uint8_tag("cmcc", 0)
        return self.daap.post(_CTRL_PROMPT_CMD, data=data)

    def controlprompt_data(self, data):
        """Perform a "controlpromptentry" command."""
        return self.daap.post(_CTRL_PROMPT_CMD, data=data)

    def set_property(self, prop, value):
        """Change value of a DAAP property, e.g. volume or media position."""
        return self.daap.post(f"ctrl-int/1/setproperty?{prop}={value}&[AUTH]")


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
        data = f"touch{direction}&time={time}&point={point1},{point2}"
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

    async def skip_forward(self, time_interval: float = 0.0) -> None:
        """Skip forward a time interval.

        Skip interval is typically 15-30s, but is decided by the app.
        """
        current_position = (await self.apple_tv.playstatus()).position
        if current_position:
            await self.set_position(
                current_position
                + (int(time_interval) if time_interval > 0 else _DEFAULT_SKIP_TIME)
            )

    async def skip_backward(self, time_interval: float = 0.0) -> None:
        """Skip backwards a time interval.

        Skip interval is typically 15-30s, but is decided by the app.
        """
        current_position = (await self.apple_tv.playstatus()).position
        if current_position:
            await self.set_position(
                current_position
                - (int(time_interval) if time_interval > 0 else _DEFAULT_SKIP_TIME)
            )

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


class DmapMetadata(Metadata):
    """Implementation of API for retrieving metadata from an Apple TV."""

    def __init__(self, identifier, apple_tv):
        """Initialize metadata instance."""
        self.identifier = identifier
        self.apple_tv = apple_tv
        self.artwork_cache = Cache(limit=4)

    @property
    def device_id(self) -> Optional[str]:
        """Return a unique identifier for current device."""
        return self.identifier

    async def artwork(
        self, width: Optional[int] = 512, height: Optional[int] = None
    ) -> Optional[ArtworkInfo]:
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


class DmapPushUpdater(AbstractPushUpdater):
    """Implementation of API for handling push update from an Apple TV."""

    def __init__(
        self, apple_tv, state_dispatcher: ProtocolStateDispatcher, listener
    ) -> None:
        """Initialize a new DmapPushUpdater instance."""
        super().__init__(state_dispatcher)
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

        self._future = asyncio.ensure_future(self._poller())

    def stop(self):
        """No longer forward updates to listener."""
        if self._future is not None:
            self._future.cancel()
            self._future = None

    async def _poller(self):
        first_call = True

        while True:
            try:
                # Sleep some time before waiting for updates
                if not first_call and self._initial_delay > 0:
                    _LOGGER.debug("Initial delay set to %d", self._initial_delay)
                    await asyncio.sleep(self._initial_delay)
                    first_call = False

                _LOGGER.debug("Waiting for playstatus updates")
                playstatus = await self._atv.playstatus(use_revision=True, timeout=0)

                self.post_update(playstatus)
            except asyncio.CancelledError:
                break

            except ClientError as ex:
                _LOGGER.exception("A communication error happened")
                listener = self._listener()
                if listener:
                    self.loop.call_soon(listener.listener.connection_lost, ex)

                break

            # It is not pretty to disable pylint here, but we must catch _all_
            # exceptions to keep the API.
            except Exception as ex:  # pylint: disable=broad-except
                _LOGGER.debug("Playstatus error occurred: %s", ex)
                self._atv.playstatus_revision = 0
                self.loop.call_soon(self.listener.playstatus_error, self, ex)

        self._future = None


class DmapFeatures(Features):
    """Implementation of API for supported feature functionality."""

    def __init__(self, config: BaseConfig, apple_tv: BaseDmapAppleTV) -> None:
        """Initialize a new DmapFeatures instance."""
        self.config = config
        self.apple_tv = apple_tv

    def get_feature(  # pylint: disable=too-many-return-statements
        self, feature_name: FeatureName
    ) -> FeatureInfo:
        """Return current state of a feature."""
        if feature_name in _AVAILABLE_FEATURES:
            return FeatureInfo(state=FeatureState.Available)
        if feature_name in _UNKNOWN_FEATURES:
            return FeatureInfo(state=FeatureState.Unknown)
        if feature_name in _FIELD_FEATURES:
            return FeatureInfo(state=self._is_available(_FIELD_FEATURES[feature_name]))
        if feature_name == FeatureName.VolumeUp:
            return FeatureInfo(state=self._is_available(("cmst", "cavc"), True))
        if feature_name == FeatureName.VolumeDown:
            return FeatureInfo(state=self._is_available(("cmst", "cavc"), True))

        return FeatureInfo(state=FeatureState.Unsupported)

    def _is_available(self, field: tuple, expected_value=None) -> FeatureState:
        if self.apple_tv.latest_playstatus:
            value = parser.first(self.apple_tv.latest_playstatus, *field)
            if value is not None:
                if not expected_value or expected_value == value:
                    return FeatureState.Available
        return FeatureState.Unavailable


class DmapAudio(Audio):
    """Implementation of API for audio functionality."""

    def __init__(self, apple_tv: BaseDmapAppleTV) -> None:
        """Initialize a new DmapAudio instance."""
        self.apple_tv = apple_tv

    async def volume_up(self) -> None:
        """Increase volume by one step."""
        await self.apple_tv.ctrl_int_cmd("volumeup")

    async def volume_down(self) -> None:
        """Decrease volume by one step."""
        await self.apple_tv.ctrl_int_cmd("volumedown")


def homesharing_service_handler(
    mdns_service: mdns.Service, response: mdns.Response
) -> Optional[ScanHandlerReturn]:
    """Parse and return a new DMAP (Home Sharing) service."""
    name = mdns_service.properties.get("Name", "Unknown")
    service = MutableService(
        get_unique_id(mdns_service.type, mdns_service.name, mdns_service.properties),
        Protocol.DMAP,
        mdns_service.port,
        mdns_service.properties,
    )
    service.credentials = mdns_service.properties.get("hG")
    return name, service


def dmap_service_handler(
    mdns_service: mdns.Service, response: mdns.Response
) -> Optional[ScanHandlerReturn]:
    """Parse and return a new DMAP service."""
    name = mdns_service.properties.get("CtlN", "Unknown")
    service = MutableService(
        get_unique_id(mdns_service.type, mdns_service.name, mdns_service.properties),
        Protocol.DMAP,
        mdns_service.port,
        mdns_service.properties,
    )
    return name, service


def hscp_service_handler(
    mdns_service: mdns.Service, response: mdns.Response
) -> Optional[ScanHandlerReturn]:
    """Parse and return a new HSCP service."""
    name = mdns_service.properties.get("Machine Name", "Unknown")
    service = MutableService(
        get_unique_id(mdns_service.type, mdns_service.name, mdns_service.properties),
        Protocol.DMAP,
        port=mdns_service.port,
        properties=mdns_service.properties,
    )
    service.credentials = mdns_service.properties.get("hG")
    return name, service


def scan() -> Mapping[str, ScanHandlerDeviceInfoName]:
    """Return handlers used for scanning."""
    return {
        "_appletv-v2._tcp.local": (homesharing_service_handler, lambda _: None),
        "_touch-able._tcp.local": (dmap_service_handler, lambda _: None),
        "_hscp._tcp.local": (hscp_service_handler, lambda _: None),
    }


def device_info(service_type: str, properties: Mapping[str, Any]) -> Dict[str, Any]:
    """Return device information from zeroconf properties."""
    devinfo: Dict[str, Any] = {}

    # Like with MRP, this is also border line OK, but will do for now
    devinfo[DeviceInfo.OPERATING_SYSTEM] = OperatingSystem.Legacy

    if service_type == "_hscp._tcp.local":
        devinfo[DeviceInfo.MODEL] = DeviceModel.Music

    return devinfo


async def service_info(
    service: MutableService,
    devinfo: DeviceInfo,
    services: Mapping[Protocol, BaseService],
) -> None:
    """Update service with additional information.

    If Home Sharing is enabled, then the "hG" property is present and can be used as
    credentials. If not enabled, then pairing must be performed.
    """
    service.pairing = (
        PairingRequirement.Optional
        if "hg" in service.properties
        else PairingRequirement.Mandatory
    )


def setup(  # pylint: disable=too-many-locals
    core: Core,
) -> Generator[SetupData, None, None]:
    """Set up a new DMAP service."""
    daap_http = HttpSession(
        core.session_manager.session,
        f"http://{core.config.address}:{core.service.port}/",
    )
    requester = DaapRequester(daap_http, core.service.credentials)
    apple_tv = BaseDmapAppleTV(requester)
    push_updater = DmapPushUpdater(
        apple_tv, core.state_dispatcher, core.device_listener
    )
    metadata = DmapMetadata(core.config.identifier, apple_tv)
    audio = DmapAudio(apple_tv)

    interfaces = {
        RemoteControl: DmapRemoteControl(apple_tv),
        Metadata: metadata,
        PushUpdater: push_updater,
        Features: DmapFeatures(core.config, apple_tv),
        Audio: audio,
    }

    async def _connect() -> bool:
        await requester.login()

        # Retrieve initial state to have volume control state
        await apple_tv.playstatus()
        return True

    def _close() -> Set[asyncio.Task]:
        push_updater.stop()
        core.device_listener.listener.connection_closed()
        return set()

    def _device_info() -> Dict[str, Any]:
        devinfo: Dict[str, Any] = {}
        for service_type in scan():
            if service_type in core.config.properties:
                dict_merge(
                    devinfo,
                    device_info(service_type, core.config.properties[service_type]),
                )
        return devinfo

    # Features managed by this protocol
    features = set([FeatureName.VolumeDown, FeatureName.VolumeUp])
    features.update(_AVAILABLE_FEATURES)
    features.update(_UNKNOWN_FEATURES)
    features.update(_FIELD_FEATURES.keys())

    yield SetupData(Protocol.DMAP, _connect, _close, _device_info, interfaces, features)


def pair(core: Core, **kwargs) -> PairingHandler:
    """Return pairing handler for protocol."""
    return DmapPairingHandler(core, **kwargs)
