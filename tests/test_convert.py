"""Unit tests for pyatv.convert."""

from pyatv import convert
from pyatv.const import DeviceState, MediaType, Protocol, RepeatState, ShuffleState


def test_media_type_to_string():
    assert "Unknown" == convert.media_type_str(MediaType.Unknown)
    assert "Video" == convert.media_type_str(MediaType.Video)
    assert "Music" == convert.media_type_str(MediaType.Music)
    assert "TV" == convert.media_type_str(MediaType.TV)


def test_unknown_media_type_to_str():
    assert "Unsupported" == convert.media_type_str(999)


def test_device_state_str():
    assert "Idle" == convert.device_state_str(DeviceState.Idle)
    assert "Loading" == convert.device_state_str(DeviceState.Loading)
    assert "Stopped" == convert.device_state_str(DeviceState.Stopped)
    assert "Paused" == convert.device_state_str(DeviceState.Paused)
    assert "Playing" == convert.device_state_str(DeviceState.Playing)
    assert "Seeking" == convert.device_state_str(DeviceState.Seeking)


def test_unsupported_device_state_str():
    assert "Unsupported" == convert.device_state_str(999)


def test_repeat_str():
    assert "Off" == convert.repeat_str(RepeatState.Off)
    assert "Track" == convert.repeat_str(RepeatState.Track)
    assert "All" == convert.repeat_str(RepeatState.All)


def test_unknown_repeat_to_str():
    assert "Unsupported" == convert.repeat_str(1234)


def test_shuffle_str():
    assert "Off" == convert.shuffle_str(ShuffleState.Off)
    assert "Albums" == convert.shuffle_str(ShuffleState.Albums)
    assert "Songs" == convert.shuffle_str(ShuffleState.Songs)


def test_unknown_shuffle_to_str():
    assert "Unsupported" == convert.shuffle_str(1234)


def test_protocol_str():
    assert "MRP" == convert.protocol_str(Protocol.MRP)
    assert "DMAP" == convert.protocol_str(Protocol.DMAP)
    assert "AirPlay" == convert.protocol_str(Protocol.AirPlay)
    assert "Companion" == convert.protocol_str(Protocol.Companion)
    assert "RAOP" == convert.protocol_str(Protocol.RAOP)


def test_unknown_protocol_str():
    assert "Unknown" == convert.protocol_str("invalid")
