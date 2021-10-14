"""Public interface exposed by library.

This module contains all the interfaces that represents a generic Apple TV device and
all its features.
"""

from abc import ABC, abstractmethod
import asyncio
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
)
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

_ALL_FEATURES = {}  # type: Dict[int, Tuple[str, str]]

ReturnType = TypeVar("ReturnType", bound=Callable[..., Any])


class ArtworkInfo(NamedTuple):
    """Artwork information."""

    bytes: bytes
    mimetype: str
    width: int
    height: int


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

        raise Exception(
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
    commands = {}  # type: Dict[str, str]
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
    ) -> None:
        """Initialize a new BaseService."""
        self._identifier = identifier
        self._protocol = protocol
        self._port = port
        self._properties: MutableMapping[str, str] = dict(properties or {})
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

    def __str__(self) -> str:
        """Return a string representation of this object."""
        return (
            f"Protocol: {convert.protocol_str(self.protocol)}, "
            f"Port: {self.port}, "
            f"Credentials: {self.credentials}, "
            f"Requires Password: {self.requires_password}, "
            f"Password: {self.password}, "
            f"Pairing: {self.pairing.name}"
        )


class PairingHandler(ABC):
    """Base class for API used to pair with an Apple TV."""

    def __init__(
        self, session_manager: ClientSessionManager, service: BaseService
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
        raise exceptions.NotSupportedError()

    @property
    @abstractmethod
    def device_provides_pin(self) -> bool:
        """Return True if remote device presents PIN code, else False."""
        raise exceptions.NotSupportedError()

    @property
    @abstractmethod
    def has_paired(self) -> bool:
        """If a successful pairing has been performed.

        The value will be reset when stop() is called.
        """
        raise exceptions.NotSupportedError()

    @abstractmethod
    async def begin(self) -> None:
        """Start pairing process."""
        raise exceptions.NotSupportedError()

    @abstractmethod
    async def finish(self) -> None:
        """Stop pairing process."""
        raise exceptions.NotSupportedError()


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
        """Press key play."""
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
    async def skip_forward(self) -> None:
        """Skip forward a time interval.

        Skip interval is typically 15-30s, but is decided by the app.
        """
        raise exceptions.NotSupportedError()

    @feature(37, "SkipBackward", "Skip backwards a time interval.")
    async def skip_backward(self) -> None:
        """Skip backwards a time interval.

        Skip interval is typically 15-30s, but is decided by the app.
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
    ]

    def __init__(
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
    ) -> None:
        """Initialize a new Playing instance."""
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
        self._post_process()

    def _post_process(self):
        if self._position:
            # Make sure position never is negative
            self._position = max(self._position, 0)

            # If there's a total time, never exceed that'
            if self._total_time:
                self._position = min(self._position, self._total_time)

    def __str__(self) -> str:
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

        return "\n".join(output)

    def __eq__(self, other):
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
    async def launch_app(self, bundle_id: str) -> None:
        """Launch an app based on bundle ID."""
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

    Listener interface: `pyatv.interface.PushListener`
    """

    def __init__(self, loop: asyncio.AbstractEventLoop):
        """Initialize a new PushUpdater."""
        super().__init__()
        self.loop = loop
        self._previous_state: Optional[Playing] = None

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

    def post_update(self, playing: Playing) -> None:
        """Post an update to listener."""
        if playing != self._previous_state:
            self.loop.call_soon(self.listener.playstatus_update, self, playing)

        self._previous_state = playing


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
    async def stream_file(self, file: Union[str, io.BufferedReader], **kwargs) -> None:
        """Stream local file to device.

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
    ):
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
    def mac(self) -> Optional[str]:
        """Device MAC address."""
        return self._mac

    def __str__(self) -> str:
        """Convert device info to readable string."""
        # If no model is available but raw_model is, use that. Otherwise fall back
        # to whatever model_str returns.
        if self.model == DeviceModel.Unknown and self.raw_model:
            model = self.raw_model
        else:
            model = convert.model_str(self.model)

        output = (
            model
            + ", "
            + {
                OperatingSystem.Legacy: "ATV SW",
                OperatingSystem.TvOS: "tvOS",
                OperatingSystem.AirPortOS: "AirPortOS",
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
    ):
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


class Audio:
    """Base class for audio functionality.

    Volume level is managed in percent where 0 is muted and 100 is max volume.
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
        for prot in [Protocol.MRP, Protocol.DMAP, Protocol.AirPlay, Protocol.RAOP]:
            service = self.get_service(prot)
            if service:
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
    def audio(self) -> Audio:
        """Return audio interface."""
