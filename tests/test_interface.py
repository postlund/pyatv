"""Unit tests for pyatv.interface."""

import unittest

from pyatv import convert, exceptions, interface
from pyatv.interface import FeatureInfo
from pyatv.const import (
    MediaType,
    DeviceState,
    RepeatState,
    ShuffleState,
    OperatingSystem,
    DeviceModel,
    FeatureState,
    FeatureName,
)


class TestClass:

    variable = 1234

    def test_method(self):
        """Help text."""
        pass

    def another_method(self):
        """Some other help text. More text here. Test."""
        pass

    @property
    def some_property(self):
        """Property help"""
        pass

    def abbrev_help(self):
        """Type, e.g. a, b or c."""
        pass

    def abbrev_help_more_text(self):
        """Type, e.g. a, b or c. Some other text."""
        pass

    def _private_method_ignored(self):
        """Not parsed."""
        pass


class PlayingDummy(interface.Playing):
    def __init__(
        self,
        media_type=MediaType.Video,
        device_state=DeviceState.Playing,
        title=None,
        artist=None,
        album=None,
        genre=None,
        total_time=None,
        position=None,
        shuffle=ShuffleState.Songs,
        repeat=RepeatState.Track,
    ):
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

    @property
    def media_type(self):
        """What type of media is currently playing, e.g. video, music."""
        return self._media_type

    @property
    def device_state(self):
        """Current device state, e.g. playing or paused."""
        return self._device_state

    @property
    def title(self):
        """Title of the current media, e.g. movie or song name."""
        return self._title

    @property
    def artist(self):
        """Artist of the currently playing song."""
        return self._artist

    @property
    def album(self):
        """Album of the currently playing song."""
        return self._album

    @property
    def genre(self):
        """Genre of the currently playing song."""
        return self._genre

    @property
    def total_time(self):
        """Total play time in seconds."""
        return self._total_time

    @property
    def position(self):
        """Current position in the playing media (seconds)."""
        return self._position

    @property
    def shuffle(self):
        """If shuffle is enabled or not."""
        return self._shuffle

    @property
    def repeat(self):
        """Current repeat mode."""
        return self._repeat


class MetadataDummy(interface.Metadata):
    def artwork(self):
        """Return artwork for what is currently playing (or None)."""
        raise exceptions.NotSupportedError()

    def artwork_id(self):
        """Return a unique identifier for current artwork."""
        raise exceptions.NotSupportedError()

    def playing(self):
        """Return what is currently playing."""
        raise exceptions.NotSupportedError()

    @property
    def app(self):
        """Return information about running app."""
        raise exceptions.NotSupportedError()


class FeaturesDummy(interface.Features):
    def __init__(self, state):
        self.state = state

    def get_feature(self, feature: FeatureName) -> FeatureInfo:
        """Return current state of a feature."""
        return FeatureInfo(state=self.state)


class InterfaceTest(unittest.TestCase):
    def setUp(self):
        self.methods = interface.retrieve_commands(TestClass)

    # COMMANDS AND HELP TEXT

    def test_get_commands(self):
        self.assertEqual(5, len(self.methods))
        self.assertTrue("test_method" in self.methods)
        self.assertTrue("another_method" in self.methods)
        self.assertTrue("some_property" in self.methods)
        self.assertTrue("abbrev_help" in self.methods)

    def test_get_first_sentence_without_leading_period_in_pydoc(self):
        self.assertEqual("Help text", self.methods["test_method"])
        self.assertEqual("Some other help text", self.methods["another_method"])
        self.assertEqual("Property help", self.methods["some_property"])

    def test_try_to_be_smart_with_abbreviations(self):
        self.assertEqual("Type, e.g. a, b or c", self.methods["abbrev_help"])
        self.assertEqual("Type, e.g. a, b or c", self.methods["abbrev_help_more_text"])

    # PLAYING STR

    def test_playing_media_type_and_playstate(self):
        out = str(PlayingDummy())
        self.assertIn(convert.media_type_str(MediaType.Video), out)
        self.assertIn(convert.device_state_str(DeviceState.Playing), out)

    def test_playing_title_artist_album_genre(self):
        out = str(
            PlayingDummy(
                title="mytitle", artist="myartist", album="myalbum", genre="mygenre"
            )
        )
        self.assertIn("mytitle", out)
        self.assertIn("myartist", out)
        self.assertIn("myalbum", out)
        self.assertIn("mygenre", out)

    def test_playing_only_position(self):
        self.assertIn("1234", str(PlayingDummy(position=1234)))

    def test_playing_only_total_time(self):
        self.assertIn("5678", str(PlayingDummy(total_time=5678)))

    def test_playing_both_position_and_total_time(self):
        out = str(PlayingDummy(position=1234, total_time=5678))
        self.assertIn("1234/5678", out)

    def test_playing_shuffle_and_repeat(self):
        out = str(PlayingDummy())
        self.assertIn("Shuffle: Songs", out)
        self.assertIn("Repeat: Track", out)

    # OTHER

    def test_playing_generate_same_hash(self):
        playing = PlayingDummy(
            title="title", artist="artist", album="album", total_time=123
        )
        self.assertEqual(
            "538df531d1715629fdd87affd0c5957bcbf54cd89180778071e6535b7df4e22c",
            playing.hash,
        )

        playing2 = PlayingDummy(
            title="dummy", artist="test", album="none", total_time=321
        )
        self.assertEqual(
            "80045c05d18382f33a5369fd5cdfc6ae42c3eb418125f638d7a31ab173b01ade",
            playing2.hash,
        )

    # METADATA

    def test_metadata_device_id(self):
        self.assertEqual(MetadataDummy("dummy").device_id, "dummy")

    # Dummy test for the sake of code coverage
    def test_metadata_rest_not_supported(self):
        metadata = MetadataDummy("dummy")

        with self.assertRaises(exceptions.NotSupportedError):
            metadata.artwork()
        with self.assertRaises(exceptions.NotSupportedError):
            metadata.artwork_id()
        with self.assertRaises(exceptions.NotSupportedError):
            metadata.playing()


class DeviceInfoTest(unittest.TestCase):
    def test_fields_set(self):
        dev_info = interface.DeviceInfo(
            OperatingSystem.TvOS,
            "1.2.3",
            "19A123",
            DeviceModel.Gen4K,
            "aa:bb:cc:dd:ee:ff",
        )

        self.assertEqual(dev_info.operating_system, OperatingSystem.TvOS)
        self.assertEqual(dev_info.version, "1.2.3")
        self.assertEqual(dev_info.build_number, "19A123")
        self.assertEqual(dev_info.model, DeviceModel.Gen4K)
        self.assertEqual(dev_info.mac, "aa:bb:cc:dd:ee:ff")

    def test_apple_tv_software_str(self):
        dev_info = interface.DeviceInfo(
            OperatingSystem.Legacy,
            "2.2.3",
            "13D333",
            DeviceModel.Gen3,
            "aa:bb:cc:dd:ee:ff",
        )

        self.assertEqual(str(dev_info), "3 ATV SW 2.2.3 build 13D333")

    def test_tvos_str(self):
        dev_info = interface.DeviceInfo(
            OperatingSystem.TvOS,
            "1.2.3",
            "19A123",
            DeviceModel.Gen4K,
            "aa:bb:cc:dd:ee:ff",
        )

        self.assertEqual(str(dev_info), "4K tvOS 1.2.3 build 19A123")

    def test_unknown_str(self):
        dev_info = interface.DeviceInfo(
            OperatingSystem.Unknown, None, None, DeviceModel.Unknown, None
        )

        self.assertEqual(str(dev_info), "Unknown Model Unknown OS")


class FeaturesTest(unittest.TestCase):
    def test_all_unsupported_features(self):
        features = FeaturesDummy(FeatureState.Unsupported)
        self.assertFalse(features.all_features())

    def test_all_include_unsupported_features(self):
        features = FeaturesDummy(FeatureState.Unsupported)
        all_features = features.all_features(include_unsupported=True)

        self.assertEqual(set(all_features.keys()), set(FeatureName))
        self.assertEqual(
            set([ft.state for ft in all_features.values()]),
            set([FeatureState.Unsupported]),
        )


class AppTest(unittest.TestCase):
    def setUp(self):
        self.app = interface.App("name", "id")

    def test_app_properties(self):
        self.assertEqual(self.app.name, "name")
        self.assertEqual(self.app.identifier, "id")

    def test_app_str(self):
        self.assertEqual("App: name (id)", str(self.app))
