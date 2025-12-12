"""Constants used in the public API."""

# pylint: disable=invalid-name

from enum import Enum

MAJOR_VERSION = "0"
MINOR_VERSION = "16"
PATCH_VERSION = "1"
__short_version__ = f"{MAJOR_VERSION}.{MINOR_VERSION}"
__version__ = f"{__short_version__}.{PATCH_VERSION}"


class Protocol(Enum):
    """All supported protocols."""

    DMAP = 1
    """Protocol constant representing DMAP."""

    MRP = 2
    """Protocol constant representing MRP."""

    AirPlay = 3
    """Protocol constant representing AirPlay."""

    Companion = 4
    """Protocol constant representing Companion link."""

    RAOP = 5
    """Protocol constant representing RAOP."""


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


class KeyboardFocusState(Enum):
    """All supported keyboard focus states."""

    Unknown = 0
    """Keyboard focus state is not determinable."""

    Unfocused = 1
    """Keyboard is not focused."""

    Focused = 2
    """Keyboard is focused."""


class OperatingSystem(Enum):
    """Operating system on device."""

    Unknown = 0
    """Operating system is not known."""

    Legacy = 1
    """Operating system  is Apple TV Software (pre-tvOS)."""

    TvOS = 2
    """Operating system is tvOS."""

    AirPortOS = 3
    """Operating system is AirPortOS.

    This OS is used by AirPort Express devices. It is not an official name but made up
    in pyatv as no official name has been found.
    """

    MacOS = 4
    """Operating system is macOS."""


class DeviceModel(Enum):
    """Hardware device model.

    Gen2-Gen4K are Apple TV model names and will be renamed to AppleTVGenX in the
    future.
    """

    Unknown = 0
    """Device model is unknown."""

    Gen2 = 1
    """Device model is second generation Apple TV (Apple TV 2)."""

    Gen3 = 2
    """Device model is third generation Apple TV (Apple TV 3)."""

    Gen4 = 3
    """Device model is fourth generation Apple TV (Apple TV 4)."""

    Gen4K = 4
    """Device model is fifth generation Apple TV (Apple TV 4K)."""

    HomePod = 5
    """Device model is HomePod (first generation)."""

    HomePodMini = 6
    """Device model is HomePod Mini (first generation)."""

    AirPortExpress = 7
    """Device model is AirPort Express (first generation)."""

    AirPortExpressGen2 = 8
    """Device model is AirPort Express (second generation)."""

    AppleTV4KGen2 = 9
    """Device model is sixth generation Apple TV (Apple TV 4K gen 2)."""

    Music = 10
    """Music app (or iTunes) running on a desktop computer."""

    AppleTV4KGen3 = 11
    """Device model is seventh generation Apple TV (Apple TV 4K gen 3)."""

    HomePodGen2 = 12
    """Device model is HomePod (second generation)."""

    AppleTVGen1 = 13
    """Device model is first generation Apple TV."""


class InputAction(Enum):
    """Type of input when pressing a button."""

    SingleTap = 0
    """Press and release quickly."""

    DoubleTap = 1
    """Press and release twice quickly."""

    Hold = 2
    """Press and hold for one second before releasing."""


class PairingRequirement(Enum):
    """Pairing requirement for a service."""

    Unsupported = 1
    """Not supported by protocol or not implemented."""

    Disabled = 2
    """Pairing is disabled by protocol."""

    NotNeeded = 3
    """Pairing is not needed."""

    Optional = 4
    """Pairing is supported but not required."""

    Mandatory = 5
    """Pairing must be performed."""


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
    """Go back to previous menu."""

    VolumeUp = 12
    """Increase volume."""

    VolumeDown = 13
    """Decrease volume."""

    Home = 14
    """Home/TV button."""

    HomeHold = 15
    """Long-press home button (deprecated: use RemoteControl.home)."""

    TopMenu = 16
    """Go to main menu."""

    Suspend = 17
    """Suspend device (deprecated; use Power.turn_off)."""

    WakeUp = 18
    """Wake up device (deprecated; use Power.turn_on)."""

    SkipForward = 36
    """Skip forward a time interval."""

    SkipBackward = 37
    """Skip backwards a time interval."""

    SetPosition = 19
    """Seek to position."""

    SetShuffle = 20
    """Change shuffle state."""

    SetRepeat = 21
    """Change repeat state."""

    ChannelUp = 48
    """Select next channel."""

    ChannelDown = 49
    """Select previous channel."""

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
    """Shuffle state."""

    Repeat = 29
    """Repeat state."""

    SeriesName = 40
    """Title of TV series."""

    SeasonNumber = 41
    """Season number of TV series."""

    EpisodeNumber = 42
    """Episode number of TV series."""

    ContentIdentifier = 47
    """Identifier for Content"""

    iTunesStoreIdentifier = 50
    """iTunes Store Identifier for Content"""

    AppList = 38
    """List of launchable apps."""

    LaunchApp = 39
    """Launch an app."""

    AccountList = 55
    """List of user accounts."""

    SwitchAccount = 56
    """Switch user account."""

    Artwork = 30
    """Playing media artwork."""

    App = 35
    """App playing media."""

    PushUpdates = 43
    """Push updates are supported."""

    PlayUrl = 31
    """Stream a URL on device."""

    StreamFile = 44
    """Stream local file to device."""

    PowerState = 32
    """Current device power state."""

    Screensaver = 58
    """Activate screen saver."""

    TurnOn = 33
    """Turn device on."""

    TurnOff = 34
    """Turn off device."""

    Volume = 45
    """Current volume level."""

    SetVolume = 46
    """Set volume level."""

    OutputDevices = 59
    """Current output devices."""

    AddOutputDevices = 60
    """Add output devices."""

    RemoveOutputDevices = 61
    """Remove output devices."""

    SetOutputDevices = 62
    """Set output devices."""

    TextFocusState = 57
    """Current virtual keyboard focus state."""

    TextGet = 51
    """Get current virtual keyboard text."""

    TextClear = 52
    """Clear virtual keyboard text."""

    TextAppend = 53
    """Input text into virtual keyboard."""

    TextSet = 54
    """Replace text in virtual keyboard."""

    Swipe = 63
    """Touch swipe from given coordinates and duration."""

    Action = 64
    """Touch event to given coordinates."""

    Click = 65
    """Touch click command."""


class TouchAction(Enum):
    """Touch action constants."""

    Press = 1
    Hold = 3
    Release = 4
    Click = 5
