"""Unit tests for pyatv.interface."""
from unittest.mock import ANY, MagicMock

import pytest
from typing import Dict, Optional

from pyatv import convert, exceptions, interface
from pyatv.interface import FeatureInfo, Playing
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


# Contains two valid values for each property that are tested
# against each other
eq_test_cases = [
    ("media_type", MediaType.Video, MediaType.Music),
    ("device_state", DeviceState.Idle, DeviceState.Playing),
    ("title", "foo", "bar"),
    ("artist", "abra", "kadabra"),
    ("album", "banana", "apple"),
    ("genre", "cat", "mouse"),
    ("total_time", 210, 2000),
    ("position", 555, 888),
    ("shuffle", ShuffleState.Albums, ShuffleState.Songs),
    ("repeat", RepeatState.Track, RepeatState.All),
    ("hash", "hash1", "hash2"),
]


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
    def __init__(self, feature_map: Dict[FeatureName, FeatureState]):
        self.feature_map = feature_map

    def get_feature(self, feature: FeatureName) -> FeatureInfo:
        """Return current state of a feature."""
        if feature not in self.feature_map:
            state = FeatureState.Unsupported
        else:
            state = self.feature_map[feature]
        return FeatureInfo(state=state)


class PushUpdaterDummy(interface.PushUpdater):
    def active(self) -> bool:
        """Return if push updater has been started."""
        raise exceptions.NotSupportedError()

    def start(self, initial_delay: int = 0) -> None:
        """Begin to listen to updates.

        If an error occurs, start must be called again.
        """
        raise exceptions.NotSupportedError()

    def stop(self) -> None:
        """No longer forward updates to listener."""
        raise exceptions.NotSupportedError()


@pytest.fixture
def methods():
    yield interface.retrieve_commands(TestClass)


# COMMANDS


def test_get_commands(methods):
    assert len(methods) == 5
    assert "test_method" in methods
    assert "another_method" in methods
    assert "some_property" in methods
    assert "abbrev_help" in methods


def test_get_first_sentence_without_leading_period_in_pydoc(methods):
    assert "Help text" == methods["test_method"]
    assert "Some other help text" == methods["another_method"]
    assert "Property help" == methods["some_property"]


def test_try_to_be_smart_with_abbreviations(methods):
    assert "Type, e.g. a, b or c" == methods["abbrev_help"]
    assert "Type, e.g. a, b or c" == methods["abbrev_help_more_text"]


# PLAYING


def test_playing_media_type_and_playstate():
    out = str(Playing(media_type=MediaType.Video, device_state=DeviceState.Playing))
    assert convert.media_type_str(MediaType.Video) in out
    assert convert.device_state_str(DeviceState.Playing) in out


def test_playing_title_artist_album_genre():
    out = str(
        Playing(title="mytitle", artist="myartist", album="myalbum", genre="mygenre")
    )
    assert "mytitle" in out
    assert "myartist" in out
    assert "myalbum" in out
    assert "mygenre" in out


def test_playing_only_position():
    assert "1234" in str(Playing(position=1234))


def test_playing_only_total_time():
    assert "5678" in str(Playing(total_time=5678))


def test_playing_both_position_and_total_time():
    out = str(Playing(position=1234, total_time=5678))
    assert "1234/5678" in out


def test_playing_shuffle_and_repeat():
    out = str(Playing(shuffle=ShuffleState.Songs, repeat=RepeatState.Track))
    assert "Shuffle: Songs" in out
    assert "Repeat: Track" in out


def test_playing_generate_same_hash():
    playing = Playing(title="title", artist="artist", album="album", total_time=123)
    assert (
        "538df531d1715629fdd87affd0c5957bcbf54cd89180778071e6535b7df4e22c"
        == playing.hash
    )

    playing2 = Playing(title="dummy", artist="test", album="none", total_time=321)

    assert (
        "80045c05d18382f33a5369fd5cdfc6ae42c3eb418125f638d7a31ab173b01ade"
        == playing2.hash
    )


def test_playing_custom_hash():
    playing = Playing(hash="dummy")
    assert playing.hash == "dummy"


def test_playing_eq_ensure_member_count():
    # Fail if a property is added or removed to interface, just as a reminder to
    # update equality comparison
    assert len(Playing().__dict__) == 11


@pytest.mark.parametrize(
    "prop,value1,value2",
    [pytest.param(*data, id=data[0]) for data in eq_test_cases],
)
def test_playing_field_equality(prop, value1, value2):
    playing1 = Playing(**{prop: value1})
    playing2 = Playing(**{prop: value2})
    playing3 = Playing(**{prop: value2})

    assert playing1 == playing1
    assert playing1 != playing2
    assert playing2 == playing3


@pytest.mark.parametrize(
    "prop,value1,value2",
    [pytest.param(*data, id=data[0]) for data in eq_test_cases],
)
def test_playing_init_field_values(prop, value1, value2):
    playing = Playing(**{prop: value1})
    assert getattr(playing, prop) == value1


# METADATA


def test_metadata_device_id():
    assert MetadataDummy("dummy").device_id == "dummy"


def test_metadata_rest_not_supported():
    metadata = MetadataDummy("dummy")

    with pytest.raises(exceptions.NotSupportedError):
        metadata.artwork()
    with pytest.raises(exceptions.NotSupportedError):
        metadata.artwork_id()
    with pytest.raises(exceptions.NotSupportedError):
        metadata.playing()


# DEVICE INFO


def test_fields_set():
    dev_info = interface.DeviceInfo(
        OperatingSystem.TvOS,
        "1.2.3",
        "19A123",
        DeviceModel.Gen4K,
        "aa:bb:cc:dd:ee:ff",
    )

    assert dev_info.operating_system == OperatingSystem.TvOS
    assert dev_info.version == "1.2.3"
    assert dev_info.build_number == "19A123"
    assert dev_info.model == DeviceModel.Gen4K
    assert dev_info.mac == "aa:bb:cc:dd:ee:ff"


def test_apple_tv_software_str():
    dev_info = interface.DeviceInfo(
        OperatingSystem.Legacy,
        "2.2.3",
        "13D333",
        DeviceModel.Gen3,
        "aa:bb:cc:dd:ee:ff",
    )

    assert str(dev_info) == "3 ATV SW 2.2.3 build 13D333"


def test_tvos_str():
    dev_info = interface.DeviceInfo(
        OperatingSystem.TvOS,
        "1.2.3",
        "19A123",
        DeviceModel.Gen4K,
        "aa:bb:cc:dd:ee:ff",
    )

    assert str(dev_info) == "4K tvOS 1.2.3 build 19A123"


def test_unknown_str():
    dev_info = interface.DeviceInfo(
        OperatingSystem.Unknown, None, None, DeviceModel.Unknown, None
    )

    assert str(dev_info) == "Unknown Model Unknown OS"


# FEATURES


def test_all_unsupported_features():
    features = FeaturesDummy({FeatureName.Play: FeatureState.Unsupported})
    assert not features.all_features()


def test_all_include_unsupported_features():
    features = FeaturesDummy({FeatureName.Play: FeatureState.Unsupported})
    all_features = features.all_features(include_unsupported=True)

    assert set(all_features.keys()) == set(FeatureName)
    assert set([ft.state for ft in all_features.values()]) == set(
        [FeatureState.Unsupported]
    )


def test_features_in_state():
    features = FeaturesDummy(
        {
            FeatureName.Play: FeatureState.Unsupported,
            FeatureName.Pause: FeatureState.Available,
        }
    )

    assert not features.in_state(FeatureState.Unknown, FeatureName.Play)
    assert not features.in_state([FeatureState.Unknown], FeatureName.Play)
    assert features.in_state(FeatureState.Unsupported, FeatureName.Play)
    assert features.in_state([FeatureState.Unsupported], FeatureName.Play)

    assert not features.in_state(
        [FeatureState.Unsupported], FeatureName.Play, FeatureName.Pause
    )

    assert features.in_state(
        [FeatureState.Unsupported, FeatureState.Available],
        FeatureName.Play,
        FeatureName.Pause,
    )


# APP


def test_app_properties():
    app = interface.App("name", "id")
    assert app.name == "name"
    assert app.identifier == "id"


def test_app_str():
    app = interface.App("name", "id")
    assert "App: name (id)" == str(app)


# PUSH UPDATER


@pytest.mark.parametrize("updates", [1, 2, 3])
def test_post_ignore_duplicate_update(event_loop, updates):
    listener = MagicMock()
    playing = Playing()

    async def _post_updates(repeats: int):
        updater = PushUpdaterDummy(event_loop)
        updater.listener = listener
        for _ in range(repeats):
            updater.post_update(playing)

    event_loop.run_until_complete(_post_updates(updates))

    assert listener.playstatus_update.call_count == 1
    listener.playstatus_update.assert_called_once_with(ANY, playing)
