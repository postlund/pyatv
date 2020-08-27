"""Public interface exposed by library.

This module contains all the interfaces that represents a generic Apple TV device and
all its features.
"""

import re
import inspect
import hashlib
from typing import (
    Any,
    Dict,
    Optional,
    NamedTuple,
    Callable,
    TypeVar,
    Tuple,
    Union,
    List,
)
import weakref

from abc import ABC, abstractmethod

from pyatv import const, convert, exceptions
from pyatv.const import (
    Protocol,
    OperatingSystem,
    DeviceModel,
    FeatureState,
    FeatureName,
    InputAction,
)
from pyatv.support import net

__pdoc__ = {}
__pdoc__["feature"] = False

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


class _ListenerProxy:
    """Proxy to call functions in a listener.

    A proxy instance maintains a weak reference to a listener object and allows calling
    functions in the listener. If no listener is set or the weak reference has expired,
    a null-function (doing nothing) is returned so that nothing happens. This makes it
    safe to call functions without having to check if either a listener has been set at
    all or if the listener implements the called function.
    """

    def __init__(self, listener):
        """Initialize a new ListenerProxy instance."""
        self.listener = listener

    def __getattr__(self, attr):
        """Dynamically find target method in listener."""
        if self.listener is not None:
            listener = self.listener()
            if hasattr(listener, attr):
                return getattr(listener, attr)

        return lambda *args, **kwargs: None


class StateProducer:
    """Base class for objects announcing state changes to a listener."""

    def __init__(self) -> None:
        """Initialize a new StateProducer instance."""
        self.__listener: Optional[weakref.ReferenceType[Any]] = None

    @property
    def listener(self):
        """Return current listener object."""
        return _ListenerProxy(self.__listener)

    @listener.setter
    def listener(self, target) -> None:
        """Change current listener object.

        Set to None to remove active listener.
        """
        if target is not None:
            self.__listener = weakref.ref(target)
        else:
            self.__listener = None


def feature(index: int, name: str, doc: str) -> Callable[[ReturnType], ReturnType]:
    """Decorate functions and properties as a feature.

    Note: This is an internal function.
    """

    def _feat_decorator(func: ReturnType) -> ReturnType:
        if index in _ALL_FEATURES:
            raise Exception(
                f"Index {index} collides between {name} and {_ALL_FEATURES[index]}"
            )
        _ALL_FEATURES[index] = (name, doc)

        return func

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


class BaseService:
    """Base class for protocol services."""

    def __init__(
        self,
        identifier: Optional[str],
        protocol: Protocol,
        port: int,
        properties: Optional[Dict[str, str]],
    ) -> None:
        """Initialize a new BaseService."""
        self.__identifier = identifier
        self.protocol = protocol
        self.port = port
        self.credentials: Optional[str] = None
        self.properties = properties or {}

    @property
    def identifier(self) -> Optional[str]:
        """Return unique identifier associated with this service."""
        return self.__identifier

    def merge(self, other) -> None:
        """Merge with other service of same type."""
        self.credentials = other.credentials or self.credentials
        self.properties.update(other.properties)

    def __str__(self) -> str:
        """Return a string representation of this object."""
        return "Protocol: {0}, Port: {1}, Credentials: {2}".format(
            convert.protocol_str(self.protocol), self.port, self.credentials
        )


class PairingHandler(ABC):
    """Base class for API used to pair with an Apple TV."""

    def __init__(
        self, session_manager: net.ClientSessionManager, service: BaseService
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


class RemoteControl(ABC):  # pylint: disable=too-many-public-methods
    """Base class for API used to control an Apple TV."""

    # pylint: disable=invalid-name
    @abstractmethod
    @feature(0, "Up", "Up button on remote.")
    async def up(self, action: InputAction = InputAction.SingleTap) -> None:
        """Press key up."""
        raise exceptions.NotSupportedError()

    @abstractmethod
    @feature(1, "Down", "Down button on remote.")
    async def down(self, action: InputAction = InputAction.SingleTap) -> None:
        """Press key down."""
        raise exceptions.NotSupportedError()

    @abstractmethod
    @feature(2, "Left", "Left button on remote.")
    async def left(self, action: InputAction = InputAction.SingleTap) -> None:
        """Press key left."""
        raise exceptions.NotSupportedError()

    @abstractmethod
    @feature(3, "Right", "Right button on remote.")
    async def right(self, action: InputAction = InputAction.SingleTap) -> None:
        """Press key right."""
        raise exceptions.NotSupportedError()

    @abstractmethod
    @feature(4, "Play", "Start playing media.")
    async def play(self) -> None:
        """Press key play."""
        raise exceptions.NotSupportedError()

    @abstractmethod
    @feature(5, "PlayPause", "Toggle between play/pause.")
    async def play_pause(self) -> None:
        """Toggle between play and pause."""
        raise exceptions.NotSupportedError()

    @abstractmethod
    @feature(6, "Pause", "Pause playing media.")
    async def pause(self) -> None:
        """Press key play."""
        raise exceptions.NotSupportedError()

    @abstractmethod
    @feature(7, "Stop", "Stop playing media.")
    async def stop(self) -> None:
        """Press key stop."""
        raise exceptions.NotSupportedError()

    @abstractmethod
    @feature(8, "Next", "Change to next item.")
    async def next(self) -> None:
        """Press key next."""
        raise exceptions.NotSupportedError()

    @abstractmethod
    @feature(9, "Previous", "Change to previous item.")
    async def previous(self) -> None:
        """Press key previous."""
        raise exceptions.NotSupportedError()

    @abstractmethod
    @feature(10, "Select", "Select current option.")
    async def select(self, action: InputAction = InputAction.SingleTap) -> None:
        """Press key select."""
        raise exceptions.NotSupportedError()

    @abstractmethod
    @feature(11, "Menu", "Go back to previous menu.")
    async def menu(self, action: InputAction = InputAction.SingleTap) -> None:
        """Press key menu."""
        raise exceptions.NotSupportedError()

    @abstractmethod
    @feature(12, "VolumeUp", "Increase volume.")
    async def volume_up(self) -> None:
        """Press key volume up."""
        raise exceptions.NotSupportedError()

    @abstractmethod
    @feature(13, "VolumeDown", "Decrease volume.")
    async def volume_down(self) -> None:
        """Press key volume down."""
        raise exceptions.NotSupportedError()

    @abstractmethod
    @feature(14, "Home", "Home/TV button.")
    async def home(self, action: InputAction = InputAction.SingleTap) -> None:
        """Press key home."""
        raise exceptions.NotSupportedError()

    @abstractmethod
    @feature(
        15, "HomeHold", "Long-press home button (deprecated: use RemoteControl.home)."
    )
    async def home_hold(self) -> None:
        """Hold key home."""
        raise exceptions.NotSupportedError()

    @abstractmethod
    @feature(16, "TopMenu", "Go to main menu.")
    async def top_menu(self) -> None:
        """Go to main menu (long press menu)."""
        raise exceptions.NotSupportedError()

    @abstractmethod
    @feature(17, "Suspend", "Suspend device (deprecated; use Power.turn_off).")
    async def suspend(self) -> None:
        """Suspend the device."""
        raise exceptions.NotSupportedError()

    @abstractmethod
    @feature(18, "WakeUp", "Wake up device (deprecated; use Power.turn_on).")
    async def wakeup(self) -> None:
        """Wake up the device."""
        raise exceptions.NotSupportedError()

    @abstractmethod
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

    @abstractmethod
    @feature(37, "SkipBackward", "Skip backwards a time interval.")
    async def skip_backward(self) -> None:
        """Skip backwards a time interval.

        Skip interval is typically 15-30s, but is decided by the app.
        """
        raise exceptions.NotSupportedError()

    @abstractmethod
    @feature(19, "SetPosition", "Seek to position.")
    async def set_position(self, pos: int) -> None:
        """Seek in the current playing media."""
        raise exceptions.NotSupportedError()

    @abstractmethod
    @feature(20, "SetShuffle", "Change shuffle state.")
    async def set_shuffle(self, shuffle_state: const.ShuffleState) -> None:
        """Change shuffle mode to on or off."""
        raise exceptions.NotSupportedError()

    @abstractmethod
    @feature(21, "SetRepeat", "Change repeat state.")
    async def set_repeat(self, repeat_state: const.RepeatState) -> None:
        """Change repeat state."""
        raise exceptions.NotSupportedError()


class Playing(ABC):
    """Base class for retrieving what is currently playing."""

    def __str__(self) -> str:
        """Convert this playing object to a readable string."""
        output = []
        output.append(
            "  Media type: {0}".format(convert.media_type_str(self.media_type))
        )
        output.append(
            "Device state: {0}".format(convert.device_state_str(self.device_state))
        )

        if self.title is not None:
            output.append("       Title: {0}".format(self.title))

        if self.artist is not None:
            output.append("      Artist: {0}".format(self.artist))

        if self.album is not None:
            output.append("       Album: {0}".format(self.album))

        if self.genre is not None:
            output.append("       Genre: {0}".format(self.genre))

        position = self.position
        total_time = self.total_time
        if position is not None and total_time is not None and total_time != 0:
            output.append(
                "    Position: {0}/{1}s ({2:.1%})".format(
                    position, total_time, float(position) / float(total_time)
                )
            )
        elif position is not None and position != 0:
            output.append("    Position: {0}s".format(position))
        elif total_time is not None and position != 0:
            output.append("  Total time: {0}s".format(total_time))

        if self.repeat is not None:
            output.append("      Repeat: {0}".format(convert.repeat_str(self.repeat)))

        if self.shuffle is not None:
            output.append("     Shuffle: {0}".format(convert.shuffle_str(self.shuffle)))

        return "\n".join(output)

    @property
    def hash(self) -> str:
        """Create a unique hash for what is currently playing.

        The hash is based on title, artist, album and total time. It should
        always be the same for the same content, but it is not guaranteed.
        """
        base = "{0}{1}{2}{3}".format(
            self.title, self.artist, self.album, self.total_time
        )
        return hashlib.sha256(base.encode("utf-8")).hexdigest()

    @property
    @abstractmethod
    def media_type(self) -> const.MediaType:
        """Type of media is currently playing, e.g. video, music."""
        raise exceptions.NotSupportedError()

    @property
    @abstractmethod
    def device_state(self) -> const.DeviceState:
        """Device state, e.g. playing or paused."""
        raise exceptions.NotSupportedError()

    @property  # type: ignore
    @abstractmethod
    @feature(22, "Title", "Title of playing media.")
    def title(self) -> Optional[str]:
        """Title of the current media, e.g. movie or song name."""
        raise exceptions.NotSupportedError()

    @property  # type: ignore
    @abstractmethod
    @feature(23, "Artist", "Artist of playing song.")
    def artist(self) -> Optional[str]:
        """Artist of the currently playing song."""
        raise exceptions.NotSupportedError()

    @property  # type: ignore
    @abstractmethod
    @feature(24, "Album", "Album from playing artist.")
    def album(self) -> Optional[str]:
        """Album of the currently playing song."""
        raise exceptions.NotSupportedError()

    @property  # type: ignore
    @abstractmethod
    @feature(25, "Genre", "Genre of playing song.")
    def genre(self) -> Optional[str]:
        """Genre of the currently playing song."""
        raise exceptions.NotSupportedError()

    @property  # type: ignore
    @abstractmethod
    @feature(26, "TotalTime", "Total length of playing media (seconds).")
    def total_time(self) -> int:
        """Total play time in seconds."""
        raise exceptions.NotSupportedError()

    @property  # type: ignore
    @abstractmethod
    @feature(27, "Position", "Current play time position.")
    def position(self) -> int:
        """Position in the playing media (seconds)."""
        raise exceptions.NotSupportedError()

    @property  # type: ignore
    @abstractmethod
    @feature(28, "Shuffle", "Shuffle stat.e")
    def shuffle(self) -> const.ShuffleState:
        """If shuffle is enabled or not."""
        raise exceptions.NotSupportedError()

    @property  # type: ignore
    @abstractmethod
    @feature(29, "Repeat", "Repeat state.")
    def repeat(self) -> const.RepeatState:
        """Repeat mode."""
        raise exceptions.NotSupportedError()


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


class Metadata(ABC):
    """Base class for retrieving metadata from an Apple TV."""

    def __init__(self, identifier: str) -> None:
        """Initialize a new instance of Metadata."""
        self._identifier = identifier

    @property
    def device_id(self) -> Optional[str]:
        """Return a unique identifier for current device."""
        return self._identifier

    @abstractmethod
    @feature(30, "Artwork", "Playing media artwork.")
    async def artwork(self, width=512, height=None) -> Optional[ArtworkInfo]:
        """Return artwork for what is currently playing (or None).

        The parameters "width" and "height" makes it possible to request artwork of a
        specific size. This is just a request, the device might impose restrictions and
        return artwork of a different size. Set both parameters to None to request
        default size. Set one of them and let the other one be None to keep original
        aspect ratio.
        """
        raise exceptions.NotSupportedError()

    @property
    @abstractmethod
    def artwork_id(self) -> str:
        """Return a unique identifier for current artwork."""
        raise exceptions.NotSupportedError()

    @abstractmethod
    async def playing(self) -> Playing:
        """Return what is currently playing."""
        raise exceptions.NotSupportedError()

    @property  # type: ignore
    @abstractmethod
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

    @property
    @abstractmethod
    def active(self) -> bool:
        """Return if push updater has been started."""
        raise exceptions.NotSupportedError()

    @abstractmethod
    def start(self, initial_delay: int = 0) -> None:
        """Begin to listen to updates.

        If an error occurs, start must be called again.
        """
        raise exceptions.NotSupportedError()

    @abstractmethod
    def stop(self) -> None:
        """No longer forward updates to listener."""
        raise exceptions.NotSupportedError()


class Stream(ABC):  # pylint: disable=too-few-public-methods
    """Base class for stream functionality."""

    @abstractmethod
    def close(self) -> None:
        """Close connection and release allocated resources."""
        raise exceptions.NotSupportedError()

    @abstractmethod
    @feature(31, "PlayUrl", "Stream a URL on device.")
    async def play_url(self, url: str, **kwargs) -> None:
        """Play media from an URL on the device."""
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
    @abstractmethod
    @feature(32, "PowerState", "Current device power state.")
    def power_state(self) -> const.PowerState:
        """Return device power state."""
        raise exceptions.NotSupportedError()

    @abstractmethod
    @feature(33, "TurnOn", "Turn device on.")
    async def turn_on(self, await_new_state: bool = False) -> None:
        """Turn device on."""
        raise exceptions.NotSupportedError()

    @abstractmethod
    @feature(34, "TurnOff", "Turn off device.")
    async def turn_off(self, await_new_state: bool = False) -> None:
        """Turn device off."""
        raise exceptions.NotSupportedError()


class DeviceInfo:
    """General information about device."""

    def __init__(
        self,
        os: const.OperatingSystem,
        version: Optional[str],
        build_number: Optional[str],
        model: const.DeviceModel,
        mac: Optional[str],
    ) -> None:  # pylint: disable=too-many-arguments  # noqa
        """Initialize a new DeviceInfo instance."""
        self._os = os
        self._version = version
        self._build_number = build_number
        self._model = model
        self._mac = mac

    @property
    def operating_system(self) -> const.OperatingSystem:
        """Operating system running on device."""
        return self._os

    @property
    def version(self) -> Optional[str]:
        """Operating system version."""
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
    def mac(self) -> Optional[str]:
        """Device MAC address."""
        return self._mac

    def __str__(self) -> str:
        """Convert device info to readable string."""
        if self.model != DeviceModel.Unknown:
            output = self.model.name.replace("Gen", "")
        else:
            output = "Unknown Model"

        output += (
            " "
            + {
                OperatingSystem.Legacy: "ATV SW",
                OperatingSystem.TvOS: "tvOS",
            }.get(self.operating_system, "Unknown OS")
        )

        if self.version:
            output += " " + self.version

        if self.build_number:
            output += " build " + self.build_number

        return output


class Features(ABC):
    """Base class for supported feature functionality."""

    @abstractmethod
    def get_feature(self, feature: FeatureName) -> FeatureInfo:
        """Return current state of a feature."""
        raise NotImplementedError()

    def all_features(self, include_unsupported=False) -> Dict[FeatureName, FeatureInfo]:
        """Return state of all features."""
        features = {}  # type: Dict[FeatureName, FeatureInfo]
        for name in FeatureName:
            feature = self.get_feature(name)
            if feature.state != FeatureState.Unsupported or include_unsupported:
                features[name] = feature
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
            feature = self.get_feature(name)
            expected_states = states if isinstance(states, list) else [states]
            if feature.state not in expected_states:
                return False
        return True


class AppleTV(ABC, StateProducer):
    """Base class representing an Apple TV.

    Listener interface: `pyatv.interfaces.DeviceListener`
    """

    @abstractmethod
    async def connect(self) -> None:
        """Initiate connection to device.

        No need to call it yourself, it's done automatically.
        """
        raise exceptions.NotSupportedError()

    @abstractmethod
    def close(self) -> None:
        """Close connection and release allocated resources."""
        raise exceptions.NotSupportedError()

    @property
    @abstractmethod
    def device_info(self) -> DeviceInfo:
        """Return API for device information."""
        raise exceptions.NotSupportedError()

    @property
    @abstractmethod
    def service(self) -> BaseService:
        """Return service used to connect to the Apple TV."""
        raise exceptions.NotSupportedError()

    @property
    @abstractmethod
    def remote_control(self) -> RemoteControl:
        """Return API for controlling the Apple TV."""
        raise exceptions.NotSupportedError()

    @property
    @abstractmethod
    def metadata(self) -> Metadata:
        """Return API for retrieving metadata from the Apple TV."""
        raise exceptions.NotSupportedError()

    @property
    @abstractmethod
    def push_updater(self) -> PushUpdater:
        """Return API for handling push update from the Apple TV."""
        raise exceptions.NotSupportedError()

    @property
    @abstractmethod
    def stream(self) -> Stream:
        """Return API for streaming media."""
        raise exceptions.NotSupportedError()

    @property
    @abstractmethod
    def power(self) -> Power:
        """Return API for power management."""
        raise exceptions.NotSupportedError()

    @property
    @abstractmethod
    def features(self) -> Features:
        """Return features interface."""
        raise exceptions.NotSupportedError()
