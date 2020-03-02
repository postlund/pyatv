"""Unit tests for pyatv.convert."""

import unittest

from pyatv import convert
from pyatv.const import Protocol, MediaType, DeviceState, RepeatState, ShuffleState


class ConvertTest(unittest.TestCase):
    def test_media_type_to_string(self):
        self.assertEqual("Unknown", convert.media_type_str(MediaType.Unknown))
        self.assertEqual("Video", convert.media_type_str(MediaType.Video))
        self.assertEqual("Music", convert.media_type_str(MediaType.Music))
        self.assertEqual("TV", convert.media_type_str(MediaType.TV))

    def test_unknown_media_type_to_str(self):
        self.assertEqual("Unsupported", convert.media_type_str(999))

    def test_device_state_str(self):
        self.assertEqual("Idle", convert.device_state_str(DeviceState.Idle))
        self.assertEqual("Loading", convert.device_state_str(DeviceState.Loading))
        self.assertEqual("Stopped", convert.device_state_str(DeviceState.Stopped))
        self.assertEqual("Paused", convert.device_state_str(DeviceState.Paused))
        self.assertEqual("Playing", convert.device_state_str(DeviceState.Playing))
        self.assertEqual("Seeking", convert.device_state_str(DeviceState.Seeking))

    def test_unsupported_device_state_str(self):
        self.assertEqual("Unsupported", convert.device_state_str(999))

    def test_repeat_str(self):
        self.assertEqual("Off", convert.repeat_str(RepeatState.Off))
        self.assertEqual("Track", convert.repeat_str(RepeatState.Track))
        self.assertEqual("All", convert.repeat_str(RepeatState.All))

    def test_unknown_repeat_to_str(self):
        self.assertEqual("Unsupported", convert.repeat_str(1234))

    def test_shuffle_str(self):
        self.assertEqual("Off", convert.shuffle_str(ShuffleState.Off))
        self.assertEqual("Albums", convert.shuffle_str(ShuffleState.Albums))
        self.assertEqual("Songs", convert.shuffle_str(ShuffleState.Songs))

    def test_unknown_shuffle_to_str(self):
        self.assertEqual("Unsupported", convert.shuffle_str(1234))

    def test_protocol_str(self):
        self.assertEqual("MRP", convert.protocol_str(Protocol.MRP))
        self.assertEqual("DMAP", convert.protocol_str(Protocol.DMAP))
        self.assertEqual("AirPlay", convert.protocol_str(Protocol.AirPlay))

    def test_unknown_protocol_str(self):
        self.assertEqual("Unknown", convert.protocol_str("invalid"))
