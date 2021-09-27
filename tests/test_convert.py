"""Unit tests for pyatv.convert."""

import pytest

from pyatv import convert
from pyatv.const import (
    DeviceModel,
    DeviceState,
    MediaType,
    Protocol,
    RepeatState,
    ShuffleState,
)


@pytest.mark.parametrize(
    "media_type,output",
    [
        (MediaType.Unknown, "Unknown"),
        (MediaType.Video, "Video"),
        (MediaType.Music, "Music"),
        (MediaType.TV, "TV"),
        (99, "Unsupported"),
    ],
)
def test_media_type_to_string(media_type, output):
    assert convert.media_type_str(media_type) == output


@pytest.mark.parametrize(
    "device_state,output",
    [
        (DeviceState.Idle, "Idle"),
        (DeviceState.Loading, "Loading"),
        (DeviceState.Stopped, "Stopped"),
        (DeviceState.Paused, "Paused"),
        (DeviceState.Playing, "Playing"),
        (DeviceState.Seeking, "Seeking"),
        (999, "Unsupported"),
    ],
)
def test_device_state_str(device_state, output):
    assert convert.device_state_str(device_state) == output


@pytest.mark.parametrize(
    "repeat,output",
    [
        (RepeatState.Off, "Off"),
        (RepeatState.Track, "Track"),
        (RepeatState.All, "All"),
        (1234, "Unsupported"),
    ],
)
def test_repeat_str(repeat, output):
    assert convert.repeat_str(repeat) == output


@pytest.mark.parametrize(
    "shuffle,output",
    [
        (ShuffleState.Off, "Off"),
        (ShuffleState.Albums, "Albums"),
        (ShuffleState.Songs, "Songs"),
        (1234, "Unsupported"),
    ],
)
def test_shuffle_str(shuffle, output):
    assert convert.shuffle_str(shuffle) == output


@pytest.mark.parametrize(
    "protocol,output",
    [
        (Protocol.MRP, "MRP"),
        (Protocol.DMAP, "DMAP"),
        (Protocol.AirPlay, "AirPlay"),
        (Protocol.Companion, "Companion"),
        (Protocol.RAOP, "RAOP"),
        (1234, "Unknown"),
    ],
)
def test_protocol_str(protocol, output):
    assert convert.protocol_str(protocol) == output


@pytest.mark.parametrize(
    "model,output",
    [
        (DeviceModel.Gen2, "Apple TV 2"),
        (DeviceModel.Gen3, "Apple TV 3"),
        (DeviceModel.Gen4, "Apple TV 4"),
        (DeviceModel.Gen4K, "Apple TV 4K"),
        (DeviceModel.HomePod, "HomePod"),
        (DeviceModel.HomePodMini, "HomePod Mini"),
        (DeviceModel.AirPortExpress, "AirPort Express (gen 1)"),
        (DeviceModel.AirPortExpressGen2, "AirPort Express (gen 2)"),
        (DeviceModel.AppleTV4KGen2, "Apple TV 4K (gen2)"),
        (DeviceModel.Music, "Music/iTunes"),
        (1234, "Unknown"),
    ],
)
def test_model_str(model, output):
    assert convert.model_str(model) == output
