"""Various types of extraction and conversion functions."""

from pyatv.const import (
    DeviceModel,
    DeviceState,
    MediaType,
    Protocol,
    RepeatState,
    ShuffleState,
)


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


def model_str(device_model: DeviceModel) -> str:
    """Convert device model to string."""
    return {
        DeviceModel.AppleTVGen1: "Apple TV 1",
        DeviceModel.Gen2: "Apple TV 2",
        DeviceModel.Gen3: "Apple TV 3",
        DeviceModel.Gen4: "Apple TV 4",
        DeviceModel.Gen4K: "Apple TV 4K",
        DeviceModel.HomePod: "HomePod",
        DeviceModel.HomePodMini: "HomePod Mini",
        DeviceModel.AirPortExpress: "AirPort Express (gen 1)",
        DeviceModel.AirPortExpressGen2: "AirPort Express (gen 2)",
        DeviceModel.AppleTV4KGen2: "Apple TV 4K (gen 2)",
        DeviceModel.Music: "Music/iTunes",
        DeviceModel.AppleTV4KGen3: "Apple TV 4K (gen 3)",
        DeviceModel.HomePodGen2: "HomePod (gen 2)",
    }.get(device_model, "Unknown")
