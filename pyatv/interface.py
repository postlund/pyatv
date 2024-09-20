"""Public interface exposed by library.

This module contains all the interfaces that represents a generic Apple TV device and
all its features.
"""

from abc import ABC, abstractmethod
import asyncio
from dataclasses import dataclass
import hashlib
import inspect
import io
from ipaddress import IPv4Address
import re
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Mapping,
    MutableMapping,
    NamedTuple,
    Optional,
    Sequence,
    Set,
    Tuple,
    TypeVar,
    Union,
)

from pyatv import const, convert, exceptions
from pyatv.const import (
    DeviceModel,
    FeatureName,
    FeatureState,
    InputAction,
    OperatingSystem,
    PairingRequirement,
    Protocol,
    TouchAction,
)
from pyatv.settings import Settings
from pyatv.support import prettydataclass
from pyatv.support.device_info import lookup_version
from pyatv.support.http import ClientSessionManager
from pyatv.support.state_producer import StateProducer

__pdoc__ = {
    "feature": False,
    "DeviceInfo.OPERATING_SYSTEM": False,
    "DeviceInfo.VERSION": False,
    "DeviceInfo.BUILD_NUMBER": False,
    "DeviceInfo.MODEL": False,
    "DeviceInfo.MAC": False,
    "DeviceInfo.RAW_MODEL": False,
}

_ALL_FEATURES: Dict[int, Tuple[str, str]] = {}

ReturnType = TypeVar(  # pylint: disable=invalid-name
    "ReturnType", bound=Callable[..., Any]
)


class ArtworkInfo(NamedTuple):
    """Artwork information."""

    bytes: bytes
    mimetype: str
    width: int
    height: int


@prettydataclass()
@dataclass
class MediaMetadata:
    """Container for media (e.g. audio or video) metadata."""

    title: Optional[str] = None
    artist: Optional[str] = None
    album: Optional[str] = None
    artwork: Optional[bytes] = None  # Raw JPEG data
    duration: Optional[float] = None


class FeatureInfo(NamedTuple):
    """Feature state and options."""

    state: FeatureState
    options: Optional[Dict[str, object]] = {}


def feature(index: int, name: str, doc: str) -> Callable[[ReturnType], ReturnType]:
    """Decorate functions and properties as a feature.

    Note: This is an internal function.
    """

    def _feat_decorator(func: ReturnType) -> ReturnType:
        if index not in _ALL_FEATURES or _ALL_FEATURES[index][0] == name:
            _ALL_FEATURES[index] = (name, doc)
            setattr(func, "_feature_name", name)
            return func

        raise RuntimeError(
            f"Index {index} collides between {name} and {_ALL_FEATURES[index]}"
        )

    return _feat_decorator


def _get_first_sentence_in_pydoc(obj):
    doc = obj.__doc__
    index = doc.find(".")
    if index == -1:
        # Here we have no leading . so return everything
        return doc

    # Try to find the first complete sentence and respect
    # abbreviations correctly
    match = re.findall(r"(.*\.[^A-Z]*)\.(?: [A-Z].*|)", doc)
    if len(match) == 1:
        return match[0]
    return doc[0:index]


def retrieve_commands(obj: object):
    """Retrieve all commands and help texts from an API object."""
    commands: Dict[str, str] = {}
    for func in obj.__dict__:
        if not inspect.isfunction(obj.__dict__[func]) and not isinstance(
            obj.__dict__[func], property
        ):
            continue
        if func.startswith("_") or func == "listener":
            continue
        commands[func] = _get_first_sentence_in_pydoc(obj.__dict__[func])
    return commands


class BaseService(ABC):
    """Base class for protocol services."""

    def __init__(
        self,
        identifier: Optional[str],
        protocol: Protocol,
        port: int,
        properties: Optional[Mapping[str, str]],
        credentials: Optional[str] = None,
        password: Optional[str] = None,
        enabled: bool = True,
    ) -> None:
        """Initialize a new BaseService."""
        self._identifier = identifier
        self._protocol = protocol
        self._port = port
        self._properties: MutableMapping[str, str] = dict(properties or {})
        self._enabled = enabled
        self.credentials: Optional[str] = credentials
        self.password: Optional[str] = password

    @property
    def identifier(self) -> Optional[str]:
        """Return unique identifier associated with this service."""
        return self._identifier

    @property
    def protocol(self) -> Protocol:
        """Return protocol type."""
        return self._protocol

    @property
    def port(self) -> int:
        """Return service port number."""
        return self._port

    @property
    def enabled(self) -> bool:
        """Return True if service is enabled."""
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        """Change whether the service is enabled or not."""
        self._enabled = value

    @property
    @abstractmethod
    def requires_password(self) -> bool:
        """Return if a password is required to access service."""

    @property
    @abstractmethod
    def pairing(self) -> PairingRequirement:
        """Return if pairing is required by service."""

    @property
    def properties(self) -> Mapping[str, str]:
        """Return service Zeroconf properties."""
        return self._properties

    def merge(self, other) -> None:
        """Merge with other service of same type.

        Merge will only include credentials, password and properties.
        """
        self.credentials = other.credentials or self.credentials
        self.password = other.password or self.password
        self._properties.update(other.properties)

    def settings(self) -> Mapping[str, Any]:
        """Return settings and their values."""
        return {
            "credentials": self.credentials,
            "password": self.password,
        }

    def apply(self, settings: Mapping[str, Any]) -> None:
        """Apply settings to service.

        Expects the same format as returned by settings() method. Unknown properties
        are silently ignored. Settings with a None value are also ignore (keeps
        original value).
        """
        self.credentials = settings.get("credentials") or self.credentials
        self.password = settings.get("password") or self.password

    def __str__(self) -> str:
        """Return a string representation of this object."""
        return (
            f"Protocol: {convert.protocol_str(self.protocol)}, "
            f"Port: {self.port}, "
            f"Credentials: {self.credentials}, "
            f"Requires Password: {self.requires_password}, "
            f"Password: {self.password}, "
            f"Pairing: {self.pairing.name}"
        ) + (" (Disabled)" if not self.enabled else "")

    @abstractmethod
    def __deepcopy__(self, memo) -> "BaseService":
        """Return deep-copy of instance."""


class PairingHandler(ABC):
    """Base class for API used to pair with an Apple TV."""

    def __init__(
        self,
        session_manager: ClientSessionManager,
        service: BaseService,
    ) -> None:
        """Initialize a new instance of PairingHandler."""
        self.session_manager = session_manager
        self._service = service

    @property
    def service(self) -> BaseService:
        """Return service used for pairing."""
        return self._service

    async def close(self) -> None:
        """Call to free allocated resources after pairing."""
        await self.session_manager.close()

    @abstractmethod
    def pin(self, pin) -> None:
        """Pin code used for pairing."""

    @property
    @abstractmethod
    def device_provides_pin(self) -> bool:
        """Return True if remote device presents PIN code, else False."""

    @property
    @abstractmethod
    def has_paired(self) -> bool:
        """If a successful pairing has been performed.

        The value will be reset when stop() is called.
        """

    @abstractmethod
    async def begin(self) -> None:
        """Start pairing process."""

    @abstractmethod
    async def finish(self) -> None:
        """Stop pairing process."""


class RemoteControl:
    """Base class for API used to control an Apple TV."""

    # pylint: disable=invalid-name
    @feature(0, "Up", "Up button on remote.")
    async def up(self, action: InputAction = InputAction.SingleTap) -> None:
        """Press key up."""
        raise exceptions.NotSupportedError()

    @feature(1, "Down", "Down button on remote.")
    async def down(self, action: InputAction = InputAction.SingleTap) -> None:
        """Press key down."""
        raise exceptions.NotSupportedError()

    @feature(2, "Left", "Left button on remote.")
    async def left(self, action: InputAction = InputAction.SingleTap) -> None:
        """Press key left."""
        raise exceptions.NotSupportedError()

    @feature(3, "Right", "Right button on remote.")
    async def right(self, action: InputAction = InputAction.SingleTap) -> None:
        """Press key right."""
        raise exceptions.NotSupportedError()

    @feature(4, "Play", "Start playing media.")
    async def play(self) -> None:
        """Press key play."""
        raise exceptions.NotSupportedError()

    @feature(5, "PlayPause", "Toggle between play/pause.")
    async def play_pause(self) -> None:
        """Toggle between play and pause."""
        raise exceptions.NotSupportedError()

    @feature(6, "Pause", "Pause playing media.")
    async def pause(self) -> None:
        """Press key pause."""
        raise exceptions.NotSupportedError()

    @feature(7, "Stop", "Stop playing media.")
    async def stop(self) -> None:
        """Press key stop."""
        raise exceptions.NotSupportedError()

    @feature(8, "Next", "Change to next item.")
    async def next(self) -> None:
        """Press key next."""
        raise exceptions.NotSupportedError()

    @feature(9, "Previous", "Change to previous item.")
    async def previous(self) -> None:
        """Press key previous."""
        raise exceptions.NotSupportedError()

    @feature(10, "Select", "Select current option.")
    async def select(self, action: InputAction = InputAction.SingleTap) -> None:
        """Press key select."""
        raise exceptions.NotSupportedError()

    @feature(11, "Menu", "Go back to previous menu.")
    async def menu(self, action: InputAction = InputAction.SingleTap) -> None:
        """Press key menu."""
        raise exceptions.NotSupportedError()

    @feature(12, "VolumeUp", "Increase volume (deprecated: use Audio.volume_up).")
    async def volume_up(self) -> None:
        """Press key volume up.

        **DEPRECATED: Use `pyatv.interface.Audio.volume_up` instead.**
        """
        raise exceptions.NotSupportedError()

    @feature(13, "VolumeDown", "Decrease volume (deprecated: use Audio.volume_down)..")
    async def volume_down(self) -> None:
        """Press key volume down.

        **DEPRECATED: Use `pyatv.interface.Audio.volume_down` instead.**
        """
        raise exceptions.NotSupportedError()

    @feature(14, "Home", "Home/TV button.")
    async def home(self, action: InputAction = InputAction.SingleTap) -> None:
        """Press key home."""
        raise exceptions.NotSupportedError()

    @feature(
        15, "HomeHold", "Long-press home button (deprecated: use RemoteControl.home)."
    )
    async def home_hold(self) -> None:
        """Hold key home."""
        raise exceptions.NotSupportedError()

    @feature(16, "TopMenu", "Go to main menu.")
    async def top_menu(self) -> None:
        """Go to main menu (long press menu)."""
        raise exceptions.NotSupportedError()

    @feature(17, "Suspend", "Suspend device (deprecated; use Power.turn_off).")
    async def suspend(self) -> None:
        """Suspend the device.

        **DEPRECATED: Use `pyatv.interface.Power.turn_off` instead.**
        """
        raise exceptions.NotSupportedError()

    @feature(18, "WakeUp", "Wake up device (deprecated; use Power.turn_on).")
    async def wakeup(self) -> None:
        """Wake up the device.

        **DEPRECATED: Use `pyatv.interface.Power.turn_on` instead.**
        """
        raise exceptions.NotSupportedError()

    @feature(
        36,
        "SkipForward",
        "Skip forward a time interval.",
    )
    async def skip_forward(self, time_interval: float = 0.0) -> None:
        """Skip forward a time interval.

        If time_interval is not positive or not present, a default or app-chosen
        time interval is used, which is typically 10, 15, 30, etc. seconds.
        """
        raise exceptions.NotSupportedError()

    @feature(37, "SkipBackward", "Skip backwards a time interval.")
    async def skip_backward(self, time_interval: float = 0.0) -> None:
        """Skip backward a time interval.

        If time_interval is not positive or not present, a default or app-chosen
        time interval is used, which is typically 10, 15, 30, etc. seconds.
        """
        raise exceptions.NotSupportedError()

    @feature(19, "SetPosition", "Seek to position.")
    async def set_position(self, pos: int) -> None:
        """Seek in the current playing media."""
        raise exceptions.NotSupportedError()

    @feature(20, "SetShuffle", "Change shuffle state.")
    async def set_shuffle(self, shuffle_state: const.ShuffleState) -> None:
        """Change shuffle mode to on or off."""
        raise exceptions.NotSupportedError()

    @feature(21, "SetRepeat", "Change repeat state.")
    async def set_repeat(self, repeat_state: const.RepeatState) -> None:
        """Change repeat state."""
        raise exceptions.NotSupportedError()

    @feature(48, "ChannelUp", "Select next channel.")
    async def channel_up(self) -> None:
        """Select next channel."""
        raise exceptions.NotSupportedError()

    @feature(49, "ChannelDown", "Select previous channel.")
    async def channel_down(self) -> None:
        """Select previous channel."""
        raise exceptions.NotSupportedError()

    @feature(58, "Screensaver", "Activate screen saver.")
    async def screensaver(self) -> None:
        """Activate screen saver.."""
        raise exceptions.NotSupportedError()


# TODO: Should be made into a dataclass when support for 3.6 is dropped
class Playing(ABC):
    """Base class for retrieving what is currently playing."""

    _PROPERTIES = [
        "media_type",
        "device_state",
        "title",
        "artist",
        "album",
        "genre",
        "total_time",
        "position",
        "shuffle",
        "repeat",
        "hash",
        "series_name",
        "season_number",
        "episode_number",
        "content_identifier",
        "itunes_store_identifier",
    ]

    def __init__(  # pylint: disable=too-many-locals
        self,
        media_type: const.MediaType = const.MediaType.Unknown,
        device_state: const.DeviceState = const.DeviceState.Idle,
        title: Optional[str] = None,
        artist: Optional[str] = None,
        album: Optional[str] = None,
        genre: Optional[str] = None,
        total_time: Optional[int] = None,
        position: Optional[int] = None,
        shuffle: Optional[const.ShuffleState] = None,
        repeat: Optional[const.RepeatState] = None,
        hash: Optional[str] = None,  # pylint: disable=redefined-builtin
        series_name: Optional[str] = None,
        season_number: Optional[int] = None,
        episode_number: Optional[int] = None,
        content_identifier: Optional[str] = None,
        itunes_store_identifier: Optional[int] = None,
    ) -> None:
        """Initialize a new Playing instance."""
        self._itunes_store_identifier = None
        self._media_type = media_type
        self._device_state = device_state
        self._title = title
        self._artist = artist
        self._album = album
        self._genre = genre
        self._total_time = total_time
        self._position = position
        self._shuffle = shuffle
        self._repeat = repeat
        self._hash = hash
        self._series_name = series_name
        self._season_number = season_number
        self._episode_number = episode_number
        self._content_identifier = content_identifier
        self._itunes_store_identifier = itunes_store_identifier

        self._post_process()

    def _post_process(self) -> None:
        if self._position:
            # Make sure position never is negative
            self._position = max(self._position, 0)

            # If there's a total time, never exceed that'
            if self._total_time:
                self._position = min(self._position, self._total_time)

    def __str__(self) -> str:  # pylint: disable=too-many-branches
        """Convert this playing object to a readable string."""
        output = []
        output.append(f"  Media type: {convert.media_type_str(self.media_type)}")
        output.append(f"Device state: {convert.device_state_str(self.device_state)}")

        if self.title is not None:
            output.append(f"       Title: {self.title}")

        if self.artist is not None:
            output.append(f"      Artist: {self.artist}")

        if self.album is not None:
            output.append(f"       Album: {self.album}")

        if self.genre is not None:
            output.append(f"       Genre: {self.genre}")

        if self.series_name is not None:
            output.append(f" Series Name: {self.series_name}")

        if self.season_number is not None:
            output.append(f"      Season: {self.season_number}")

        if self.episode_number is not None:
            output.append(f"     Episode: {self.episode_number}")

        if self.content_identifier:
            output.append(f"  Identifier: {self.content_identifier}")

        position = self.position
        total_time = self.total_time
        if position is not None and total_time is not None and total_time != 0:
            output.append(
                f"    Position: {position}/{total_time}s "
                f"({float(position) / float(total_time):.1%})"
            )
        elif position is not None and position != 0:
            output.append(f"    Position: {position}s")
        elif total_time is not None and position != 0:
            output.append(f"  Total time: {total_time}s")

        if self.repeat is not None:
            output.append(f"      Repeat: {convert.repeat_str(self.repeat)}")

        if self.shuffle is not None:
            output.append(f"     Shuffle: {convert.shuffle_str(self.shuffle)}")

        if self._itunes_store_identifier is not None:
            output.append(f"iTunes Store Identifier: {self._itunes_store_identifier}")
        return "\n".join(output)

    def __eq__(self, other) -> bool:
        """Compare if two objects are equal."""
        if isinstance(other, Playing):
            for prop in self._PROPERTIES:
                if getattr(self, prop) != getattr(other, prop):
                    return False
            return True
        return False

    @property
    def hash(self) -> str:
        """Create a unique hash for what is currently playing.

        The hash is based on title, artist, album and total time. It should
        always be the same for the same content, but it is not guaranteed.
        """
        if self._hash:
            return self._hash

        base = f"{self.title}{self.artist}{self.album}{self.total_time}"
        return hashlib.sha256(base.encode("utf-8")).hexdigest()

    @property
    def media_type(self) -> const.MediaType:
        """Type of media is currently playing, e.g. video, music."""
        return self._media_type

    @property
    def device_state(self) -> const.DeviceState:
        """Device state, e.g. playing or paused."""
        return self._device_state

    @property  # type: ignore
    @feature(22, "Title", "Title of playing media.")
    def title(self) -> Optional[str]:
        """Title of the current media, e.g. movie or song name."""
        return self._title

    @property  # type: ignore
    @feature(23, "Artist", "Artist of playing song.")
    def artist(self) -> Optional[str]:
        """Artist of the currently playing song."""
        return self._artist

    @property  # type: ignore
    @feature(24, "Album", "Album from playing artist.")
    def album(self) -> Optional[str]:
        """Album of the currently playing song."""
        return self._album

    @property  # type: ignore
    @feature(25, "Genre", "Genre of playing song.")
    def genre(self) -> Optional[str]:
        """Genre of the currently playing song."""
        return self._genre

    @property  # type: ignore
    @feature(26, "TotalTime", "Total length of playing media (seconds).")
    def total_time(self) -> Optional[int]:
        """Total play time in seconds."""
        return self._total_time

    @property  # type: ignore
    @feature(27, "Position", "Current play time position.")
    def position(self) -> Optional[int]:
        """Position in the playing media (seconds)."""
        return self._position

    @property  # type: ignore
    @feature(28, "Shuffle", "Shuffle state.")
    def shuffle(self) -> Optional[const.ShuffleState]:
        """If shuffle is enabled or not."""
        return self._shuffle

    @property  # type: ignore
    @feature(29, "Repeat", "Repeat state.")
    def repeat(self) -> Optional[const.RepeatState]:
        """Repeat mode."""
        return self._repeat

    @property  # type: ignore
    @feature(40, "SeriesName", "Title of TV series.")
    def series_name(self) -> Optional[str]:
        """Title of TV series."""
        return self._series_name

    @property  # type: ignore
    @feature(41, "SeasonNumber", "Season number of TV series.")
    def season_number(self) -> Optional[int]:
        """Season number of TV series."""
        return self._season_number

    @property  # type: ignore
    @feature(42, "EpisodeNumber", "Episode number of TV series.")
    def episode_number(self) -> Optional[int]:
        """Episode number of TV series."""
        return self._episode_number

    @property  # type: ignore
    @feature(47, "ContentIdentifier", "Identifier for Content")
    def content_identifier(self) -> Optional[str]:
        """Content identifier (app specific)."""
        return self._content_identifier

    @property  # type: ignore
    @feature(50, "iTunesStoreIdentifier", "iTunes Store identifier for Content")
    def itunes_store_identifier(self) -> Optional[int]:
        """Itunes Store identifier."""
        return self._itunes_store_identifier


class App:
    """Information about an app."""

    def __init__(self, name: Optional[str], identifier: str) -> None:
        """Initialize a new App instance."""
        self._name = name
        self._identifier = identifier

    @property
    def name(self) -> Optional[str]:
        """User friendly name of app."""
        return self._name

    @property
    def identifier(self) -> str:
        """Return a unique bundle id for the app."""
        return self._identifier

    def __str__(self) -> str:
        """Convert app info to readable string."""
        return f"App: {self.name} ({self.identifier})"

    def __eq__(self, other) -> bool:
        """Return self==other."""
        if isinstance(other, App):
            return self.name == other.name and self.identifier == other.identifier
        return False


class Apps:
    """Base class for app handling."""

    @feature(38, "AppList", "List of launchable apps.")
    async def app_list(self) -> List[App]:
        """Fetch a list of apps that can be launched."""
        raise exceptions.NotSupportedError()

    @feature(39, "LaunchApp", "Launch an app.")
    async def launch_app(self, bundle_id_or_url: str) -> None:
        """Launch an app based on bundle ID or URL."""
        raise exceptions.NotSupportedError()


class UserAccount:
    """Information about a user account."""

    def __init__(self, name: str, identifier: str) -> None:
        """Initialize a new UserAccount instance."""
        self._name = name
        self._identifier = identifier

    @property
    def name(self) -> Optional[str]:
        """User name."""
        return self._name

    @property
    def identifier(self) -> str:
        """Return a unique id for the account."""
        return self._identifier

    def __str__(self) -> str:
        """Convert account info to readable string."""
        return f"Account: {self.name} ({self.identifier})"

    def __eq__(self, other) -> bool:
        """Return self==other."""
        if isinstance(other, UserAccount):
            return self.name == other.name and self.identifier == other.identifier
        return False


class UserAccounts:
    """Base class for account handling."""

    @feature(55, "AccountList", "List of user accounts.")
    async def account_list(self) -> List[UserAccount]:
        """Fetch a list of user accounts that can be switched."""
        raise exceptions.NotSupportedError()

    @feature(56, "SwitchAccount", "Switch user account.")
    async def switch_account(self, account_id: str) -> None:
        """Switch user account by account ID."""
        raise exceptions.NotSupportedError()


class Metadata:
    """Base class for retrieving metadata from an Apple TV."""

    @property
    def device_id(self) -> Optional[str]:
        """Return a unique identifier for current device."""
        raise exceptions.NotSupportedError()

    @feature(30, "Artwork", "Playing media artwork.")
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
        raise exceptions.NotSupportedError()

    @property
    def artwork_id(self) -> str:
        """Return a unique identifier for current artwork."""
        raise exceptions.NotSupportedError()

    async def playing(self) -> Playing:
        """Return what is currently playing."""
        raise exceptions.NotSupportedError()

    @property  # type: ignore
    @feature(35, "App", "App playing media.")
    def app(self) -> Optional[App]:
        """Return information about current app playing something.

        Do note that this property returns which app is currently playing something and
        not which app is currently active. If nothing is playing, the corresponding
        feature will be unavailable.
        """
        raise exceptions.NotSupportedError()


class PushListener(ABC):
    """Listener interface for push updates."""

    @abstractmethod
    def playstatus_update(self, updater, playstatus: Playing) -> None:
        """Inform about changes to what is currently playing."""

    @abstractmethod
    def playstatus_error(self, updater, exception: Exception) -> None:
        """Inform about an error when updating play status."""


class PushUpdater(ABC, StateProducer):
    """Base class for push/async updates from an Apple TV.

    A `pyatv.interface.PushUpdater` shall only publish update in case the state
    actually changes.

    Listener interface: `pyatv.interface.PushListener`.
    """

    @property
    @abstractmethod
    def active(self) -> bool:
        """Return if push updater has been started."""
        raise NotImplementedError

    @feature(43, "PushUpdates", "Push updates are supported.")
    @abstractmethod
    def start(self, initial_delay: int = 0) -> None:
        """Begin to listen to updates.

        If an error occurs, start must be called again.
        """
        raise NotImplementedError

    @abstractmethod
    def stop(self) -> None:
        """No longer forward updates to listener."""
        raise NotImplementedError


class Stream:  # pylint: disable=too-few-public-methods
    """Base class for stream functionality."""

    def close(self) -> None:  # pylint: disable=no-self-use
        """Close connection and release allocated resources."""
        raise exceptions.NotSupportedError()

    @feature(31, "PlayUrl", "Stream a URL on device.")
    async def play_url(self, url: str, **kwargs) -> None:
        """Play media from an URL on the device."""
        raise exceptions.NotSupportedError()

    @feature(44, "StreamFile", "Stream local file to device.")
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
        raise exceptions.NotSupportedError()


class DeviceListener(ABC):
    """Listener interface for generic device updates."""

    @abstractmethod
    def connection_lost(self, exception: Exception) -> None:
        """Device was unexpectedly disconnected."""
        raise NotImplementedError()

    @abstractmethod
    def connection_closed(self) -> None:
        """Device connection was (intentionally) closed."""
        raise NotImplementedError()


class PowerListener(ABC):  # pylint: disable=too-few-public-methods
    """Listener interface for power updates."""

    @abstractmethod
    def powerstate_update(
        self, old_state: const.PowerState, new_state: const.PowerState
    ) -> None:
        """Device power state was updated."""
        raise NotImplementedError()


class Power(ABC, StateProducer):
    """Base class for retrieving power state from an Apple TV.

    Listener interface: `pyatv.interfaces.PowerListener`
    """

    @property  # type: ignore
    @feature(32, "PowerState", "Current device power state.")
    def power_state(self) -> const.PowerState:
        """Return device power state."""
        raise exceptions.NotSupportedError()

    @feature(33, "TurnOn", "Turn device on.")
    async def turn_on(self, await_new_state: bool = False) -> None:
        """Turn device on."""
        raise exceptions.NotSupportedError()

    @feature(34, "TurnOff", "Turn off device.")
    async def turn_off(self, await_new_state: bool = False) -> None:
        """Turn device off."""
        raise exceptions.NotSupportedError()


class DeviceInfo:
    """General information about device."""

    OPERATING_SYSTEM = "os"
    VERSION = "version"
    BUILD_NUMBER = "build_number"
    MODEL = "model"
    RAW_MODEL = "raw_model"
    MAC = "mac"
    OUTPUT_DEVICE_ID = "airplay_id"

    def __init__(self, device_info: Mapping[str, Any]) -> None:
        """Initialize a new DeviceInfo instance."""
        self._devinfo = device_info
        self._os = self._pop_with_type(
            self.OPERATING_SYSTEM, OperatingSystem.Unknown, OperatingSystem
        )
        self._version = self._pop_with_type(self.VERSION, None, str)
        self._build_number = self._pop_with_type(self.BUILD_NUMBER, None, str)
        self._model = self._pop_with_type(self.MODEL, DeviceModel.Unknown, DeviceModel)
        self._mac = self._pop_with_type(self.MAC, None, str)
        self._output_device_id = self._pop_with_type(self.OUTPUT_DEVICE_ID, None, str)

    def _pop_with_type(self, field, default, expected_type):
        value = self._devinfo.pop(field, default)
        if value is None or isinstance(value, expected_type):
            return value
        raise TypeError(
            f"expected {expected_type} for '{field}'' but got {type(value)}"
        )

    @property
    def operating_system(self) -> const.OperatingSystem:
        """Operating system running on device."""
        if self._os != OperatingSystem.Unknown:
            return self._os

        if self.model in [DeviceModel.AirPortExpress, DeviceModel.AirPortExpressGen2]:
            return OperatingSystem.AirPortOS
        if self.model in [DeviceModel.HomePod, DeviceModel.HomePodMini]:
            return OperatingSystem.TvOS
        if self.model in [
            DeviceModel.Gen2,
            DeviceModel.Gen3,
            DeviceModel.Gen4,
            DeviceModel.Gen4K,
            DeviceModel.AppleTV4KGen2,
            DeviceModel.AppleTV4KGen3,
        ]:
            return OperatingSystem.TvOS

        return OperatingSystem.Unknown

    @property
    def version(self) -> Optional[str]:
        """Operating system version."""
        if self._version:
            return self._version

        version = lookup_version(self.build_number)
        if version:
            return version

        return self._version

    @property
    def build_number(self) -> Optional[str]:
        """Operating system build number, e.g. 17K795."""
        return self._build_number

    @property
    def model(self) -> const.DeviceModel:
        """Hardware model name, e.g. 3, 4 or 4K."""
        return self._model

    @property
    def raw_model(self) -> Optional[str]:
        """Return raw model description.

        If `pyatv.interface.DeviceInfo.model` returns `pyatv.const.DeviceModel.Unknown`
        then this property contains the raw model string (if any is available).
        """
        return self._devinfo.get(DeviceInfo.RAW_MODEL)

    @property
    def model_str(self) -> str:
        """Return model name as string.

        This property will return the model name as a string and fallback to `raw_model`
        if it is not available.
        """
        return (
            self.raw_model
            if self.model == DeviceModel.Unknown and self.raw_model
            else convert.model_str(self.model)
        )

    @property
    def mac(self) -> Optional[str]:
        """Device MAC address."""
        return self._mac

    @property
    def output_device_id(self) -> Optional[str]:
        """Output device identifier."""
        return self._output_device_id

    def __str__(self) -> str:
        """Convert device info to readable string."""
        output = (
            self.model_str
            + ", "
            + {
                OperatingSystem.Legacy: "ATV SW",
                OperatingSystem.TvOS: "tvOS",
                OperatingSystem.AirPortOS: "AirPortOS",
                OperatingSystem.MacOS: "MacOS",
            }.get(self.operating_system, "Unknown OS")
        )

        if self.version:
            output += " " + self.version

        if self.build_number:
            output += " build " + self.build_number

        return output


class Features:
    """Base class for supported feature functionality."""

    def get_feature(self, feature_name: FeatureName) -> FeatureInfo:
        """Return current state of a feature."""
        raise NotImplementedError()

    def all_features(self, include_unsupported=False) -> Dict[FeatureName, FeatureInfo]:
        """Return state of all features."""
        features: Dict[FeatureName, FeatureInfo] = {}
        for name in FeatureName:
            info = self.get_feature(name)
            if info.state != FeatureState.Unsupported or include_unsupported:
                features[name] = info
        return features

    def in_state(
        self,
        states: Union[List[FeatureState], FeatureState],
        *feature_names: FeatureName
    ) -> bool:
        """Return if features are in a specific state.

        This method will return True if all given features are in the state specified
        by "states". If "states" is a list of states, it is enough for the feature to be
        in one of the listed states.
        """
        for name in feature_names:
            info = self.get_feature(name)
            expected_states = states if isinstance(states, list) else [states]
            if info.state not in expected_states:
                return False
        return True


class OutputDevice:
    """Information about an output device."""

    def __init__(self, name: Optional[str], identifier: str) -> None:
        """Initialize a new OutputDevice instance."""
        self._name = name
        self._identifier = identifier

    @property
    def name(self) -> Optional[str]:
        """User friendly name of output device."""
        return self._name

    @property
    def identifier(self) -> str:
        """Return a unique id for the output device."""
        return self._identifier

    def __str__(self) -> str:
        """Convert app info to readable string."""
        return f"Device: {self.name} ({self.identifier})"

    def __eq__(self, other) -> bool:
        """Return self==other."""
        if isinstance(other, OutputDevice):
            return self.name == other.name and self.identifier == other.identifier
        return False


class AudioListener(ABC):
    """Listener interface for audio updates."""

    @abstractmethod
    def volume_update(self, old_level: float, new_level: float) -> None:
        """Device volume was updated."""
        raise NotImplementedError()

    @abstractmethod
    def outputdevices_update(
        self, old_devices: List[OutputDevice], new_devices: List[OutputDevice]
    ) -> None:
        """Output devices were updated."""
        raise NotImplementedError()


class Audio(ABC, StateProducer):
    """Base class for audio functionality.

    Volume level is managed in percent where 0 is muted and 100 is max volume.


    Listener interface: `pyatv.interfaces.AudioListener`
    """

    @property  # type: ignore
    @feature(45, "Volume", "Current volume level.")
    def volume(self) -> float:
        """Return current volume level.

        Range is in percent, i.e. [0.0-100.0].
        """
        raise exceptions.NotSupportedError()

    @feature(46, "SetVolume", "Set volume level.")
    async def set_volume(self, level: float) -> None:
        """Change current volume level.

        Range is in percent, i.e. [0.0-100.0].
        """
        raise exceptions.NotSupportedError()

    @feature(12, "VolumeUp", "Increase volume.")
    async def volume_up(self) -> None:
        """Increase volume by one step.

        Step size is device dependent, but usually around 2,5% of the total volume
        range. It is not necessarily linear.

        Call will block until volume change has been acknowledged by the device (when
        possible and supported).
        """
        raise exceptions.NotSupportedError()

    @feature(13, "VolumeDown", "Decrease volume.")
    async def volume_down(self) -> None:
        """Decrease volume by one step.

        Step size is device dependent, but usually around 2.5% of the total volume
        range. It is not necessarily linear.

        Call will block until volume change has been acknowledged by the device (when
        possible and supported).
        """
        raise exceptions.NotSupportedError()

    @property  # type: ignore
    @feature(59, "OutputDevices", "Current output devices.")
    def output_devices(self) -> List[OutputDevice]:
        """Return current list of output device IDs."""
        raise exceptions.NotSupportedError()

    @feature(60, "AddOutputDevices", "Add output devices.")
    async def add_output_devices(self, *devices: List[str]) -> None:
        """Add output devices."""
        raise exceptions.NotSupportedError()

    @feature(61, "RemoveOutputDevices", "Remove output devices.")
    async def remove_output_devices(self, *devices: List[str]) -> None:
        """Remove output devices."""
        raise exceptions.NotSupportedError()

    @feature(62, "SetOutputDevices", "Set output devices.")
    async def set_output_devices(self, *devices: List[str]) -> None:
        """Set output devices."""
        raise exceptions.NotSupportedError()


class KeyboardListener(ABC):  # pylint: disable=too-few-public-methods
    """Listener interface for keyboard updates."""

    @abstractmethod
    def focusstate_update(
        self, old_state: const.KeyboardFocusState, new_state: const.KeyboardFocusState
    ) -> None:
        """Keyboard focus state was updated."""
        raise exceptions.NotSupportedError()


class Keyboard(ABC, StateProducer):
    """Base class for keyboard handling.

    Listener
    interface: `pyatv.interfaces.KeyboardListener`
    """

    @property
    @feature(57, "TextFocusState", "Current virtual keyboard focus state.")
    def text_focus_state(self) -> const.KeyboardFocusState:
        """Return keyboard focus state."""
        raise exceptions.NotSupportedError()

    @feature(51, "TextGet", "Get current virtual keyboard text.")
    async def text_get(self) -> Optional[str]:
        """Get current virtual keyboard text."""
        raise exceptions.NotSupportedError()

    @feature(52, "TextClear", "Clear virtual keyboard text.")
    async def text_clear(self) -> None:
        """Clear virtual keyboard text."""
        raise exceptions.NotSupportedError()

    @feature(53, "TextAppend", "Input text into virtual keyboard.")
    async def text_append(self, text: str) -> None:
        """Input text into virtual keyboard."""
        raise exceptions.NotSupportedError()

    @feature(54, "TextSet", "Replace text in virtual keyboard.")
    async def text_set(self, text: str) -> None:
        """Replace text in virtual keyboard."""
        raise exceptions.NotSupportedError()


class TouchGestures(ABC):
    """Base class for touch gestures."""

    @feature(63, "Swipe", "Swipe gesture from given coordinates and duration.")
    async def swipe(
        self, start_x: int, start_y: int, end_x: int, end_y: int, duration_ms: int
    ) -> None:
        """Generate a swipe gesture.

         From start to end x,y coordinates (in range [0,1000])
         in a given time (in milliseconds).

        :param start_x: Start x coordinate
        :param start_y: Start y coordinate
        :param end_x: End x coordinate
        :param end_y: Endi x coordinate
        :param duration_ms: Time in milliseconds to reach the end coordinates
        """
        raise exceptions.NotSupportedError()

    @feature(64, "TouchAction", "Touch event to given coordinates.")
    async def action(self, x: int, y: int, mode: TouchAction) -> None:
        """Generate a touch event to x,y coordinates (in range [0,1000]).

        :param x: x coordinate
        :param y: y coordinate
        :param mode: touch mode (1: press, 3: hold, 4: release)
        """
        raise exceptions.NotSupportedError()

    @feature(65, "TouchClick", "Touch click command.")
    async def click(self, action: InputAction):
        """Send a touch click.

        :param action: action mode single tap (0), double tap (1), or hold (2)
        """
        raise exceptions.NotSupportedError()


class BaseConfig(ABC):
    """Representation of a device configuration.

    An instance of this class represents a single device. A device can have
    several services depending on the protocols it supports, e.g. DMAP or
    AirPlay.
    """

    def __init__(self, properties: Mapping[str, Mapping[str, Any]]) -> None:
        """Initialize a new BaseConfig instance."""
        self._properties = properties

    @property
    @abstractmethod
    def address(self) -> IPv4Address:
        """IP address of device."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of device."""

    @property
    @abstractmethod
    def deep_sleep(self) -> bool:
        """If device is in deep sleep."""

    @property
    @abstractmethod
    def services(self) -> List[BaseService]:
        """Return all supported services."""

    @property
    @abstractmethod
    def device_info(self) -> DeviceInfo:
        """Return general device information."""

    @abstractmethod
    def add_service(self, service: BaseService) -> None:
        """Add a new service.

        If the service already exists, it will be merged.
        """

    @abstractmethod
    def get_service(self, protocol: Protocol) -> Optional[BaseService]:
        """Look up a service based on protocol.

        If a service with the specified protocol is not available, None is
        returned.
        """

    @property
    def properties(self) -> Mapping[str, Mapping[str, str]]:
        """Return Zeroconf properties."""
        return self._properties

    @property
    def ready(self) -> bool:
        """Return if configuration is ready, (at least one service with identifier)."""
        for service in self.services:
            if service.identifier:
                return True
        return False

    @property
    def identifier(self) -> Optional[str]:
        """Return the main identifier associated with this device."""
        for prot in [
            Protocol.MRP,
            Protocol.DMAP,
            Protocol.AirPlay,
            Protocol.RAOP,
            Protocol.Companion,
        ]:
            service = self.get_service(prot)
            if service and service.identifier is not None:
                return service.identifier
        return None

    @property
    def all_identifiers(self) -> List[str]:
        """Return all unique identifiers for this device."""
        return [x.identifier for x in self.services if x.identifier is not None]

    def main_service(self, protocol: Optional[Protocol] = None) -> BaseService:
        """Return suggested service used to establish connection."""
        protocols = (
            [protocol]
            if protocol is not None
            else [Protocol.MRP, Protocol.DMAP, Protocol.AirPlay, Protocol.RAOP]
        )

        for prot in protocols:
            service = self.get_service(prot)
            if service is not None:
                return service

        raise exceptions.NoServiceError("no service to connect to")

    def set_credentials(self, protocol: Protocol, credentials: str) -> bool:
        """Set credentials for a protocol if it exists."""
        service = self.get_service(protocol)
        if service:
            service.credentials = credentials
            return True
        return False

    def apply(self, settings: Settings) -> None:
        """Apply settings to configuration."""
        for service in self.services:
            if service.protocol == Protocol.AirPlay:
                service.apply(dict(settings.protocols.airplay))
            elif service.protocol == Protocol.Companion:
                service.apply(dict(settings.protocols.companion))
            elif service.protocol == Protocol.DMAP:
                service.apply(dict(settings.protocols.dmap))
            elif service.protocol == Protocol.MRP:
                service.apply(dict(settings.protocols.mrp))
            elif service.protocol == Protocol.RAOP:
                service.apply(dict(settings.protocols.raop))

    def __eq__(self, other) -> bool:
        """Compare instance with another instance."""
        if isinstance(other, self.__class__):
            return self.identifier == other.identifier
        return False

    def __str__(self) -> str:
        """Return a string representation of this object."""
        device_info = self.device_info
        services = "\n".join([f" - {s}" for s in self.services])
        identifiers = "\n".join([f" - {x}" for x in self.all_identifiers])
        return (
            f"       Name: {self.name}\n"
            f"   Model/SW: {device_info}\n"
            f"    Address: {self.address}\n"
            f"        MAC: {self.device_info.mac}\n"
            f" Deep Sleep: {self.deep_sleep}\n"
            f"Identifiers:\n"
            f"{identifiers}\n"
            f"Services:\n"
            f"{services}"
        )

    @abstractmethod
    def __deepcopy__(self, memo) -> "BaseConfig":
        """Return deep-copy of instance."""


class Storage(ABC):
    """Base class for storage modules."""

    @property
    @abstractmethod
    def settings(self) -> Sequence[Settings]:
        """Return settings for all devices."""

    @abstractmethod
    async def save(self) -> None:
        """Save settings to active storage."""

    @abstractmethod
    async def load(self) -> None:
        """Load settings from active storage."""

    @abstractmethod
    async def get_settings(self, config: BaseConfig) -> Settings:
        """Return settings for a specific configuration (device).

        The returned Settings object is a reference to an object in the storage module.
        Changes made can/will be written back to the storage in case "save" is called.

        If no settings exists for the current configuration, new settings are created
        automatically and returned. If the configuration does not contain any valid
        identitiers, DeviceIdMissingError will be raised.
        """

    @abstractmethod
    async def remove_settings(self, settings: Settings) -> bool:
        """Remove settings from storage.

        Returns True if settings were removed, otherwise False.
        """

    @abstractmethod
    async def update_settings(self, config: BaseConfig) -> None:
        """Update settings based on config.

        This method extracts settings from a configuration and writes them back to
        the storage.
        """


class AppleTV(ABC, StateProducer[DeviceListener]):
    """Base class representing an Apple TV.

    Listener interface: `pyatv.interfaces.DeviceListener`
    """

    @abstractmethod
    async def connect(self) -> None:
        """Initiate connection to device.

        No need to call it yourself, it's done automatically.
        """

    @abstractmethod
    def close(self) -> Set[asyncio.Task]:
        """Close connection and release allocated resources."""

    @property
    @abstractmethod
    def settings(self) -> Settings:
        """Return device settings used by pyatv."""

    @property
    @abstractmethod
    def device_info(self) -> DeviceInfo:
        """Return API for device information."""

    @property
    @abstractmethod
    def service(self) -> BaseService:
        """Return service used to connect to the Apple TV."""

    @property
    @abstractmethod
    def remote_control(self) -> RemoteControl:
        """Return API for controlling the Apple TV."""

    @property
    @abstractmethod
    def metadata(self) -> Metadata:
        """Return API for retrieving metadata from the Apple TV."""

    @property
    @abstractmethod
    def push_updater(self) -> PushUpdater:
        """Return API for handling push update from the Apple TV."""

    @property
    @abstractmethod
    def stream(self) -> Stream:
        """Return API for streaming media."""

    @property
    @abstractmethod
    def power(self) -> Power:
        """Return API for power management."""

    @property
    @abstractmethod
    def features(self) -> Features:
        """Return features interface."""

    @property
    @abstractmethod
    def apps(self) -> Apps:
        """Return apps interface."""

    @property
    @abstractmethod
    def user_accounts(self) -> UserAccounts:
        """Return user accounts interface."""

    @property
    @abstractmethod
    def audio(self) -> Audio:
        """Return audio interface."""

    @property
    @abstractmethod
    def keyboard(self) -> Keyboard:
        """Return keyboard interface."""

    @property
    @abstractmethod
    def touch(self) -> TouchGestures:
        """Return touch gestures interface."""
