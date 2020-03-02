"""Constants used in the public API."""

from enum import Enum


MAJOR_VERSION = '0'
MINOR_VERSION = '4'
PATCH_VERSION = '1a1'
__short_version__ = '{}.{}'.format(MAJOR_VERSION, MINOR_VERSION)
__version__ = '{}.{}'.format(__short_version__, PATCH_VERSION)


class Protocol(Enum):
    """All supported protocol."""

    DMAP = 1
    MRP = 2
    AirPlay = 3


class MediaType(Enum):
    """All suuported media types."""

    Unknown = 0
    Video = 1
    Music = 2
    TV = 3


class DeviceState(Enum):
    """All supported device states."""

    Idle = 0
    Loading = 1
    Paused = 2
    Playing = 3
    Stopped = 4
    Seeking = 5


class RepeatState(Enum):
    """All supported repeat states."""

    Off = 0
    Track = 1
    All = 2


class ShuffleState(Enum):
    """All supported shuffle states."""

    Off = 0
    Albums = 1
    Songs = 2


class PowerState(Enum):
    """All supported power states."""

    Unknown = 0
    Off = 1
    On = 2


class OperatingSystem(Enum):
    """Operating system on device."""

    Unknown = 0
    Legacy = 1  # Pre-tvOS (Apple TV Software)
    TvOS = 2


class DeviceModel(Enum):
    """Hardware device models."""

    Unknown = 0
    Gen2 = 1
    Gen3 = 2
    Gen4 = 3
    Gen4K = 4
