"""Constants used in the public API."""

from enum import Enum


MAJOR_VERSION = "0"
MINOR_VERSION = "5"
PATCH_VERSION = "0"
__short_version__ = "{}.{}".format(MAJOR_VERSION, MINOR_VERSION)
__version__ = "{}.{}".format(__short_version__, PATCH_VERSION)


class Protocol(Enum):
    """All supported protocols."""

    DMAP = 1
    """Protocol constant representing DMAP."""

    MRP = 2
    """Protocol constant representing MRP."""

    AirPlay = 3
    """Protocol constant representing AirPlay."""


class MediaType(Enum):
    """All supported media types."""

    Unknown = 0
    """Media type is not known.

    This can be either the case that nothing is playing or the app does
    not report a valid media type.
    """

    Video = 1
    """Media type is video."""

    Music = 2
    """Media type is music."""

    TV = 3
    """Media type is a TV show."""


class DeviceState(Enum):
    """All supported device states."""

    Idle = 0
    """Device is idling, i.e. nothing is playing or about to play."""

    Loading = 1
    """Media is being loaded but not yet playing."""

    Paused = 2
    """Media is in paused state."""

    Playing = 3
    """Media is playing."""

    Stopped = 4
    """Media is stopped."""

    Seeking = 5
    """Media is seeking, e.g fast forward."""


class RepeatState(Enum):
    """All supported repeat states."""

    Off = 0
    """Repeat is off."""

    Track = 1
    """Repeat current track or item."""

    All = 2
    """Repeat all tracks or items."""


class ShuffleState(Enum):
    """All supported shuffle states."""

    Off = 0
    """Shuffle is off."""

    Albums = 1
    """Shuffle on album level."""

    Songs = 2
    """Shuffle on song level."""


class PowerState(Enum):
    """All supported power states."""

    Unknown = 0
    """Power state is not determinable."""

    Off = 1
    """Device is turned off (standby)."""

    On = 2
    """Device is turned on."""


class OperatingSystem(Enum):
    """Operating system on device."""

    Unknown = 0
    """Operating system is not known."""

    Legacy = 1
    """Operating system  is Apple TV Software (pre-tvOS)."""

    TvOS = 2
    """Operating system is tvOS."""


class DeviceModel(Enum):
    """Hardware device model."""

    Unknown = 0
    """Device model is unknown."""

    Gen2 = 1
    """Device model is second generation (Apple TV 2)."""

    Gen3 = 2
    """Device model is third generation (Apple TV 3)."""

    Gen4 = 3
    """Device model is fourth generation (Apple TV 4)."""

    Gen4K = 4
    """Device model is Apple TV 4K."""


class FeatureState(Enum):
    """State of a particular feature."""

    Unknown = 0
    """Feature is supported by device but it is not known if it is available or not."""

    Unsupported = 1
    """Device does not support this feature."""

    Unavailable = 2
    """Feature is supported by device but not available now.

    Pause is for instance unavailable if nothing is playing.
    """

    Available = 3
    """Feature is supported and available."""


# This enum is generated by scripts/features.py
class FeatureName(Enum):
    """All supported features."""

    Up = 0
    """Up button on remote."""

    Down = 1
    """Down button on remote."""

    Left = 2
    """Left button on remote."""

    Right = 3
    """Right button on remote."""

    Play = 4
    """Start playing media."""

    PlayPause = 5
    """Toggle between play/pause."""

    Pause = 6
    """Pause playing media."""

    Stop = 7
    """Stop playing media."""

    Next = 8
    """Change to next item."""

    Previous = 9
    """Change to previous item."""

    Select = 10
    """Select current option."""

    Menu = 11
    """Go back to previos menu."""

    VolumeUp = 12
    """Increase volume."""

    VolumeDown = 13
    """Decrease volume."""

    Home = 14
    """Home/TV button."""

    HomeHold = 15
    """Long-press home button."""

    TopMenu = 16
    """Go to main menu."""

    Suspend = 17
    """Suspend device (deprecated; use Power.turn_off)."""

    WakeUp = 18
    """Wake up device (deprecated; use Power.turn_on)."""

    SetPosition = 19
    """Seek to position."""

    SetShuffle = 20
    """Change shuffle state."""

    SetRepeat = 21
    """Change repeat state."""

    Title = 22
    """Title of playing media."""

    Artist = 23
    """Artist of playing song."""

    Album = 24
    """Album from playing artist."""

    Genre = 25
    """Genre of playing song."""

    TotalTime = 26
    """Total length of playing media (seconds)."""

    Position = 27
    """Current play time position."""

    Shuffle = 28
    """Shuffle stat.e"""

    Repeat = 29
    """Repeat state."""

    Artwork = 30
    """Playing media artwork."""

    App = 35
    """App playing media."""

    PlayUrl = 31
    """Stream a URL on device."""

    PowerState = 32
    """Current device power state."""

    TurnOn = 33
    """Turn device on."""

    TurnOff = 34
    """Turn off device."""
