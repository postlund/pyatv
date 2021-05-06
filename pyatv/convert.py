"""Various types of extraction and conversion functions."""

from pyatv.const import DeviceState, MediaType, Protocol, RepeatState, ShuffleState


def device_state_str(state: DeviceState) -> str:
    """Convert internal API device state to string."""
    return {
        None: "Idle",
        DeviceState.Idle: "Idle",
        DeviceState.Loading: "Loading",
        DeviceState.Stopped: "Stopped",
        DeviceState.Paused: "Paused",
        DeviceState.Playing: "Playing",
        DeviceState.Seeking: "Seeking",
    }.get(state, "Unsupported")


def media_type_str(mediatype: MediaType) -> str:
    """Convert internal API media type to string."""
    return {
        MediaType.Unknown: "Unknown",
        MediaType.Video: "Video",
        MediaType.Music: "Music",
        MediaType.TV: "TV",
    }.get(mediatype, "Unsupported")


def repeat_str(state: RepeatState) -> str:
    """Convert internal API repeat state to string."""
    return {
        RepeatState.Off: "Off",
        RepeatState.Track: "Track",
        RepeatState.All: "All",
    }.get(state, "Unsupported")


def shuffle_str(state: ShuffleState) -> str:
    """Convert internal API shuffle state to string."""
    return {
        ShuffleState.Off: "Off",
        ShuffleState.Albums: "Albums",
        ShuffleState.Songs: "Songs",
    }.get(state, "Unsupported")


def protocol_str(protocol: Protocol) -> str:
    """Convert internal API protocol to string."""
    return {
        Protocol.MRP: "MRP",
        Protocol.DMAP: "DMAP",
        Protocol.AirPlay: "AirPlay",
        Protocol.Companion: "Companion",
        Protocol.RAOP: "RAOP",
    }.get(protocol, "Unknown")
