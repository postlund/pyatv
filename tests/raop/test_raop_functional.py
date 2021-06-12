"""RAOP functional tests with fake device.

TODO: Things to improve:

* Add tests for timing server
* Improve sync tests
"""

import asyncio
import logging
import math
from typing import Dict, List

import pytest

from pyatv import exceptions, raop
from pyatv.const import DeviceState, FeatureName, FeatureState, MediaType
from pyatv.interface import FeatureInfo, Playing, PushListener

from tests.utils import data_path, until

pytestmark = pytest.mark.asyncio

_LOGGER = logging.getLogger(__name__)

# Number of frames per audio packet in RAOP
FRAMES_PER_PACKET = 352

METADATA_FIELDS = [FeatureName.Title, FeatureName.Artist, FeatureName.Album]
PROGRESS_FIELDS = [FeatureName.Position, FeatureName.TotalTime]
VOLUME_FIELDS = [
    FeatureName.SetVolume,
    FeatureName.Volume,
    FeatureName.VolumeUp,
    FeatureName.VolumeDown,
]


@pytest.fixture(name="playing_listener")
async def playing_listener_fixture(raop_client):
    class PlayingListener(PushListener):
        def __init__(self):
            """Initialize a new PlayingListener instance."""
            self.updates: List[Playing] = []
            self.all_features: Dict[FeatureName, FeatureInfo] = {}
            self.playing_event = asyncio.Event()

        def playstatus_update(self, updater, playstatus: Playing) -> None:
            """Inform about changes to what is currently playing."""
            self.updates.append(playstatus)
            if playstatus.device_state == DeviceState.Playing:
                self.all_features = raop_client.features.all_features()
                self.playing_event.set()

        def playstatus_error(self, updater, exception: Exception) -> None:
            """Inform about an error when updating play status."""

    listener = PlayingListener()
    raop_client.push_updater.listener = listener
    raop_client.push_updater.start()
    yield listener


def audio_matches(
    audio: bytes,
    frames: int,
    channels: int = 2,
    sample_size: int = 2,
    skip_frames: int = 0,
) -> None:
    """Assert that raw audio matches audio generated by audiogen.py."""
    succeeded = True
    frame_size = channels * sample_size

    # assert per individual frame
    for i in range(frames):
        actual = audio[i * frame_size : i * frame_size + frame_size]
        expected = frame_size * bytes([(i + skip_frames) & 0xFF])
        if actual != expected:
            _LOGGER.error("%s != %s for frame %d", actual, expected, (i + skip_frames))
            succeeded = False

    return succeeded


def assert_features_in_state(
    all_features: Dict[FeatureName, FeatureInfo],
    features: List[FeatureName],
    state: FeatureState,
) -> None:
    for feature in features:
        assert all_features[feature].state == state


@pytest.mark.parametrize(
    "raop_properties,metadata",
    [
        # Metadata supported by receiver ("md=0")
        (
            {"et": "0", "md": "0"},
            {"artist": "postlund", "album": "raop", "title": "pyatv"},
        ),
        # Metadata NOT supported by receiver
        (
            {"et": "0"},
            {"artist": None, "album": None, "title": None},
        ),
    ],
)
async def test_stream_file_verify_metadata(raop_client, raop_state, metadata):
    await raop_client.stream.stream_file(data_path("only_metadata.wav"))
    assert raop_state.metadata.artist == metadata["artist"]
    assert raop_state.metadata.album == metadata["album"]
    assert raop_state.metadata.title == metadata["title"]


@pytest.mark.parametrize("raop_properties", [({"et": "0"})])
async def test_stream_complete_file(raop_client, raop_state):
    await raop_client.stream.stream_file(data_path("audio_10_frames.wav"))

    assert audio_matches(raop_state.raw_audio, frames=10)


@pytest.mark.parametrize("raop_properties", [({"et": "4"})])
async def test_stream_complete_legacy_auth(raop_client, raop_state, raop_usecase):
    raop_usecase.require_auth(True)

    await raop_client.stream.stream_file(data_path("audio_10_frames.wav"))

    assert raop_state.auth_setup_performed
    assert audio_matches(raop_state.raw_audio, frames=10)


@pytest.mark.parametrize(
    "raop_properties,drop_packets,enable_retransmission",
    [({"et": "0"}, 0, True), ({"et": "0"}, 2, False), ({"et": "0"}, 2, True)],
)
async def test_stream_retransmission(
    raop_client, raop_state, raop_usecase, drop_packets, enable_retransmission
):
    raop_usecase.retransmissions_enabled(enable_retransmission)
    raop_usecase.drop_n_packets(drop_packets)

    await raop_client.stream.stream_file(data_path("audio_3_packets.wav"))

    # For stability reasons: wait for all packets to be received as it might take a few
    # extra runs for the event loop to catch up
    packets_to_receive = 3 if enable_retransmission else 1
    await until(lambda: len(raop_state.audio_packets) == packets_to_receive)

    # If retransmissions are enabled, then we should always receive all packets in
    # the end (within reasons). If retransmissions are not enabled, then we should
    # start comparing the received audio stream after the amount of audio packets
    # dropped.
    start_frame = 0 if enable_retransmission else drop_packets * FRAMES_PER_PACKET
    assert audio_matches(
        raop_state.raw_audio,
        frames=3 * FRAMES_PER_PACKET - start_frame,  # Total expected frame
        skip_frames=start_frame,  # Skipping first amount of frames
    )


@pytest.mark.parametrize("raop_properties", [({"et": "0"})])
async def test_push_updates(raop_client, playing_listener):
    await raop_client.stream.stream_file(data_path("only_metadata.wav"))

    # Initial idle + audio playing + back to idle
    await until(lambda: len(playing_listener.updates) == 3)

    idle = playing_listener.updates[0]
    assert idle.device_state == DeviceState.Idle
    assert idle.media_type == MediaType.Unknown

    playing = playing_listener.updates[1]
    assert playing.device_state == DeviceState.Playing
    assert playing.media_type == MediaType.Music
    assert playing.artist == "postlund"
    assert playing.title == "pyatv"
    assert playing.album == "raop"

    idle = playing_listener.updates[2]
    assert idle.device_state == DeviceState.Idle
    assert idle.media_type == MediaType.Unknown


@pytest.mark.parametrize("raop_properties", [({"et": "0"})])
async def test_push_updates_progress(raop_client, playing_listener):
    assert_features_in_state(
        raop_client.features.all_features(),
        PROGRESS_FIELDS,
        FeatureState.Unavailable,
    )

    await raop_client.stream.stream_file(data_path("static_3sec.ogg"))

    # Initial idle + audio playing + back to idle
    await until(lambda: len(playing_listener.updates) == 3)

    playing = playing_listener.updates[1]
    assert playing.device_state == DeviceState.Playing
    assert playing.position == 0
    assert playing.total_time == 3

    assert_features_in_state(
        playing_listener.all_features,
        PROGRESS_FIELDS,
        FeatureState.Available,
    )


@pytest.mark.parametrize("raop_properties", [({"et": "0"})])
async def test_metadata_features(raop_client, playing_listener):
    # All features should be unavailable when nothing is playing
    assert_features_in_state(
        raop_client.features.all_features(),
        METADATA_FIELDS,
        FeatureState.Unavailable,
    )

    # StreamFile should be available for streaming
    assert (
        raop_client.features.get_feature(FeatureName.StreamFile).state
        == FeatureState.Available
    )
    await raop_client.stream.stream_file(data_path("only_metadata.wav"))

    # Use a listener to catch when something starts playing and save that as it's
    # too late to verify when stream_file returns (idle state will be reported).
    await until(lambda: playing_listener.all_features)

    # When playing, everything should be available
    assert_features_in_state(
        playing_listener.all_features,
        METADATA_FIELDS,
        FeatureState.Available,
    )


@pytest.mark.parametrize("raop_properties", [({"et": "0"})])
async def test_sync_packets(raop_client, raop_state):
    await raop_client.stream.stream_file(data_path("only_metadata.wav"))

    # TODO: This test doesn't really test anything, just makes sure that sync packets
    # are received. Expand this test in the future.
    await until(lambda: raop_state.sync_packets_received > 5)


@pytest.mark.parametrize(
    "raop_properties,feedback_supported", [({"et": "0"}, True), ({"et": "0"}, False)]
)
async def test_send_feedback(raop_client, raop_usecase, raop_state, feedback_supported):
    raop_usecase.feedback_enabled(feedback_supported)

    await raop_client.stream.stream_file(data_path("audio_3_packets.wav"))

    # One request is sent to see if feedback is supported, then additional requests are
    # only sent if actually supported
    if feedback_supported:
        assert raop_state.feedback_packets_received > 1
    else:
        assert raop_state.feedback_packets_received == 1


@pytest.mark.parametrize("raop_properties", [({"et": "0"})])
async def test_set_volume_prior_to_streaming(raop_client, raop_state):
    # Initial client sound level
    assert math.isclose(raop_client.audio.volume, 33.0)

    await raop_client.audio.set_volume(60)
    assert math.isclose(raop_client.audio.volume, 60)

    await raop_client.stream.stream_file(data_path("only_metadata.wav"))
    assert math.isclose(raop_state.volume, -12.0)


@pytest.mark.parametrize(
    "raop_properties,initial_level_supported,sender_expected,receiver_expected",
    [
        # Device supports default level: use that
        ({"et": "0"}, True, 50.0, -15.0),
        # Device does NOT support default level: use pyatv default
        ({"et": "0"}, False, 33.0, -20.1),
    ],
)
async def test_use_default_volume_from_device(
    raop_client,
    raop_state,
    raop_usecase,
    initial_level_supported,
    sender_expected,
    receiver_expected,
):
    raop_usecase.initial_audio_level_supported(initial_level_supported)

    # Prior to streaming, we don't know the volume of the receiver so return default level
    assert math.isclose(raop_client.audio.volume, 33.0)

    # Default level on remote device
    assert math.isclose(raop_state.volume, -15.0)

    await raop_client.stream.stream_file(data_path("only_metadata.wav"))

    # Level on the client and receiver should match now
    assert math.isclose(raop_state.volume, receiver_expected)
    assert math.isclose(raop_client.audio.volume, sender_expected)


@pytest.mark.parametrize("raop_properties", [({"et": "0"})])
async def test_set_volume_during_playback(raop_client, raop_state, playing_listener):
    # Set maximum volume as initial volume
    await raop_client.audio.set_volume(100.0)

    # Start playback in the background
    future = asyncio.ensure_future(
        raop_client.stream.stream_file(data_path("audio_3_packets.wav"))
    )

    # Wait for device to move to playing state and verify volume
    await playing_listener.playing_event.wait()
    assert math.isclose(raop_state.volume, -0.0)

    # Change volume, which we now know will happen during playback
    await raop_client.audio.set_volume(50.0)
    assert math.isclose(raop_state.volume, -15.0)

    await future


@pytest.mark.parametrize("raop_properties", [({"et": "0"})])
async def test_volume_features(raop_client):
    assert_features_in_state(
        raop_client.features.all_features(), VOLUME_FIELDS, FeatureState.Available
    )


@pytest.mark.parametrize("raop_properties", [({"et": "0"})])
async def test_volume_up_volume_down(raop_client):
    # Only test on the client as other tests should confirm that it is set correctly
    # on the receiver
    await raop_client.audio.set_volume(95.0)

    # Increase by 5% if volume_up is called
    await raop_client.remote_control.volume_up()
    assert math.isclose(raop_client.audio.volume, 100.0)

    # Stop at max level without any error
    await raop_client.remote_control.volume_up()
    assert math.isclose(raop_client.audio.volume, 100.0)

    await raop_client.audio.set_volume(5.0)

    # Decrease by 5% if volume_down is called
    await raop_client.remote_control.volume_down()
    assert math.isclose(raop_client.audio.volume, 0.0)

    # Stop at min level without any error
    await raop_client.remote_control.volume_down()
    assert math.isclose(raop_client.audio.volume, 0.0)


@pytest.mark.parametrize("raop_properties", [({"et": "0"})])
async def test_only_allow_one_stream_at_the_time(raop_client):
    # This is not pretty, but the idea is to start two concurrent streaming tasks, wait
    # for them to finish and verify that one of them raised an exception. This is to
    # avoid making any assumptions regarding in which order they are scheduled on the
    # event loop.
    result = await asyncio.gather(
        raop_client.stream.stream_file(data_path("audio_3_packets.wav")),
        raop_client.stream.stream_file(data_path("only_metadata.wav")),
        return_exceptions=True,
    )

    result.remove(None)  # Should be one None for success and one exception
    assert len(result) == 1
    assert isinstance(result[0], exceptions.InvalidStateError)
