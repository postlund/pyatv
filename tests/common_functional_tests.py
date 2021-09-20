"""Common functional tests for all protocols."""

import asyncio
import logging
from pathlib import Path
from typing import Optional

from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop

import pyatv
from pyatv import exceptions, interface
from pyatv.conf import AppleTV, ManualService
from pyatv.const import (
    DeviceState,
    FeatureName,
    FeatureState,
    InputAction,
    MediaType,
    Protocol,
    RepeatState,
    ShuffleState,
)

from tests.utils import data_path, faketime, stub_sleep, unstub_sleep, until

_LOGGER = logging.getLogger(__name__)

ARTWORK_BYTES = b"1234"
ARTWORK_BYTES2 = b"4321"
ARTWORK_MIMETYPE = "image/png"
ARTWORK_WIDTH = 512
ARTWORK_HEIGHT = 512
ARTWORK_ID = "artwork_id1"
EXAMPLE_STREAM = "http://stream"


async def poll(fn, **kwargs):
    result = await fn()
    conds = [getattr(result, f) == val for f, val in kwargs.items()]
    return all(conds), result


class DummyDeviceListener(interface.DeviceListener):
    def __init__(self):
        self.closed_sem = asyncio.Semaphore(0)
        self.lost_sem = asyncio.Semaphore(0)

    def connection_lost(self, exception):
        self.lost_sem.release()

    def connection_closed(self):
        self.closed_sem.release()


class CommonFunctionalTests(AioHTTPTestCase):
    def setUp(self):
        AioHTTPTestCase.setUp(self)
        stub_sleep()

    def tearDown(self):
        unstub_sleep()
        AioHTTPTestCase.tearDown(self)

    async def get_application(self, loop=None):
        raise NotImplementedError()

    async def playing(self, **kwargs):
        return await until(poll, fn=self.atv.metadata.playing, **kwargs)

    def assertFeatures(self, state, *features):
        for feature in features:
            self.assertEqual(
                self.atv.features.get_feature(feature).state,
                state,
                f"{feature} has wrong state",
            )

    async def wait_for_button_press(self, button: str, action: Optional[InputAction]):
        await until(lambda: self.state.last_button_pressed == button)
        await until(lambda: self.state.last_button_action == action)

    def supported_volume_controls(self):
        return [FeatureName.VolumeUp, FeatureName.VolumeDown]

    @unittest_run_loop
    async def test_connect_missing_device_id(self):
        conf = AppleTV("1.2.3.4", "Apple TV")
        conf.add_service(ManualService(None, Protocol.Companion, 1234, {}))

        with self.assertRaises(exceptions.DeviceIdMissingError):
            await pyatv.connect(conf, self.loop)

    @unittest_run_loop
    async def test_connect_no_service(self):
        conf = AppleTV("1.2.3.4", "Apple TV")

        with self.assertRaises(exceptions.NoServiceError):
            await pyatv.connect(conf, self.loop, protocol=Protocol.AirPlay)

    @unittest_run_loop
    async def test_pair_missing_service(self):
        conf = AppleTV("1.2.3.4", "Apple TV")

        with self.assertRaises(exceptions.NoServiceError):
            await pyatv.pair(conf, Protocol.DMAP, self.loop)

    @unittest_run_loop
    async def test_invalid_credentials_format(self):
        self.conf.main_service().credentials = "bad"

        with self.assertRaises(exceptions.InvalidCredentialsError):
            await pyatv.connect(self.conf, loop=self.loop)

    @unittest_run_loop
    async def test_invalid_airplay_credentials_format(self):
        self.conf.get_service(Protocol.AirPlay).credentials = "bad"
        self.airplay_usecase.airplay_require_authentication()

        with self.assertRaises(exceptions.InvalidCredentialsError):
            await pyatv.connect(self.conf, loop=self.loop)

    @unittest_run_loop
    async def test_play_url(self):
        self.airplay_usecase.airplay_playback_idle()
        self.airplay_usecase.airplay_playback_playing()
        self.airplay_usecase.airplay_playback_idle()

        await self.atv.stream.play_url(EXAMPLE_STREAM, port=self.server.port)

        self.assertEqual(self.airplay_state.last_airplay_url, EXAMPLE_STREAM)

        self.atv.stream.close()

    @unittest_run_loop
    async def test_play_url_not_authenticated_error(self):
        self.conf.get_service(Protocol.AirPlay).credentials = None
        self.airplay_usecase.airplay_always_fail_authentication()

        with self.assertRaises(exceptions.AuthenticationError):
            await self.atv.stream.play_url(EXAMPLE_STREAM, port=self.server.port)

    @unittest_run_loop
    async def test_play_url_authenticated(self):
        self.airplay_usecase.airplay_require_authentication()
        self.airplay_usecase.airplay_playback_idle()
        self.airplay_usecase.airplay_playback_playing()
        self.airplay_usecase.airplay_playback_idle()

        await self.atv.stream.play_url(EXAMPLE_STREAM, port=self.server.port)

        self.assertEqual(self.airplay_state.last_airplay_url, EXAMPLE_STREAM)

    # This is not a very good test as it doesn't really test that much. Once I get
    # around improving the AirPlay testing situation this should be improved.
    @unittest_run_loop
    async def test_play_local_file(self):
        self.airplay_usecase.airplay_playback_idle()
        self.airplay_usecase.airplay_playback_playing()
        self.airplay_usecase.airplay_playback_idle()

        await self.atv.stream.play_url(data_path("testfile.txt"))

        self.assertRegex(
            self.airplay_state.last_airplay_url, r"http://127.0.0.1:[0-9]+/testfile.txt"
        )
        self.assertEqual(self.airplay_state.last_airplay_start, 0)
        self.assertIsNotNone(self.airplay_state.last_airplay_uuid)
        self.assertEqual(self.airplay_state.last_airplay_content, b"a file for testing")

    @unittest_run_loop
    async def test_button_up(self):
        await self.atv.remote_control.up()
        await self.wait_for_button_press("up", InputAction.SingleTap)

    @unittest_run_loop
    async def test_button_down(self):
        await self.atv.remote_control.down()
        await self.wait_for_button_press("down", InputAction.SingleTap)

    @unittest_run_loop
    async def test_button_left(self):
        await self.atv.remote_control.left()
        await self.wait_for_button_press("left", InputAction.SingleTap)

    @unittest_run_loop
    async def test_button_right(self):
        await self.atv.remote_control.right()
        await self.wait_for_button_press("right", InputAction.SingleTap)

    @unittest_run_loop
    async def test_button_select(self):
        await self.atv.remote_control.select()
        await self.wait_for_button_press("select", InputAction.SingleTap)

    @unittest_run_loop
    async def test_button_menu(self):
        await self.atv.remote_control.menu()
        await self.wait_for_button_press("menu", InputAction.SingleTap)

    @unittest_run_loop
    async def test_button_play(self):
        await self.atv.remote_control.play()
        await self.wait_for_button_press("play", None)

    @unittest_run_loop
    async def test_button_pause(self):
        await self.atv.remote_control.pause()
        await self.wait_for_button_press("pause", None)

    @unittest_run_loop
    async def test_button_stop(self):
        await self.atv.remote_control.stop()
        await self.wait_for_button_press("stop", None)

    @unittest_run_loop
    async def test_button_next(self):
        await self.atv.remote_control.next()
        await self.wait_for_button_press("nextitem", None)

    @unittest_run_loop
    async def test_button_previous(self):
        await self.atv.remote_control.previous()
        await self.wait_for_button_press("previtem", None)

    @unittest_run_loop
    async def test_button_volume_up(self):
        await self.atv.remote_control.volume_up()
        await until(lambda: self.state.last_button_pressed == "volumeup")

    @unittest_run_loop
    async def test_button_volume_down(self):
        await self.atv.remote_control.volume_down()
        await until(lambda: self.state.last_button_pressed == "volumedown")

    def test_metadata_device_id(self):
        self.assertIn(self.atv.metadata.device_id, self.conf.all_identifiers)

    @unittest_run_loop
    async def test_close_connection(self):
        listener = DummyDeviceListener()
        self.atv.listener = listener
        self.atv.close()

        await asyncio.wait_for(listener.closed_sem.acquire(), timeout=3.0)

    @unittest_run_loop
    async def test_metadata_video_paused(self):
        self.usecase.video_playing(
            paused=True, title="dummy", total_time=100, position=3
        )

        with faketime("pyatv", 0):
            playing = await self.playing(title="dummy")
            self.assertEqual(playing.media_type, MediaType.Video)
            self.assertEqual(playing.device_state, DeviceState.Paused)
            self.assertEqual(playing.title, "dummy")
            self.assertEqual(playing.total_time, 100)
            self.assertEqual(playing.position, 3)

    @unittest_run_loop
    async def test_metadata_video_playing(self):
        self.usecase.video_playing(
            paused=False, title="video", total_time=40, position=10
        )

        with faketime("pyatv", 0):
            playing = await self.playing(title="video")
            self.assertEqual(playing.media_type, MediaType.Video)
            self.assertEqual(playing.device_state, DeviceState.Playing)
            self.assertEqual(playing.title, "video")
            self.assertEqual(playing.total_time, 40)
            self.assertEqual(playing.position, 10)

    @unittest_run_loop
    async def test_metadata_music_paused(self):
        self.usecase.music_playing(
            paused=True,
            title="music",
            artist="artist",
            album="album",
            total_time=222,
            position=49,
            genre="genre",
        )

        with faketime("pyatv", 0):
            playing = await self.playing(title="music")
            self.assertEqual(playing.media_type, MediaType.Music)
            self.assertEqual(playing.device_state, DeviceState.Paused)
            self.assertEqual(playing.title, "music")
            self.assertEqual(playing.artist, "artist")
            self.assertEqual(playing.album, "album")
            self.assertEqual(playing.genre, "genre")
            self.assertEqual(playing.total_time, 222)
            self.assertEqual(playing.position, 49)

    @unittest_run_loop
    async def test_metadata_music_playing(self):
        self.usecase.music_playing(
            paused=False,
            title="music",
            artist="test1",
            album="test2",
            total_time=2,
            position=1,
            genre="genre",
        )

        with faketime("pyatv", 0):
            playing = await self.playing(title="music")
            self.assertEqual(playing.media_type, MediaType.Music)
            self.assertEqual(playing.device_state, DeviceState.Playing)
            self.assertEqual(playing.title, "music")
            self.assertEqual(playing.artist, "test1")
            self.assertEqual(playing.album, "test2")
            self.assertEqual(playing.genre, "genre")
            self.assertEqual(playing.total_time, 2)
            self.assertEqual(playing.position, 1)

    @unittest_run_loop
    async def test_seek_in_playing_media(self):
        self.usecase.video_playing(
            paused=False, title="dummy", total_time=40, position=10
        )

        with faketime("pyatv", 0):
            await self.atv.remote_control.set_position(30)
            playing = await self.playing(position=30)
            self.assertEqual(playing.position, 30)

    @unittest_run_loop
    async def test_metadata_artwork(self):
        self.usecase.example_video()
        self.usecase.change_artwork(ARTWORK_BYTES, ARTWORK_MIMETYPE)

        await self.playing(title="dummy")
        artwork = await self.atv.metadata.artwork()
        self.assertIsNotNone(artwork)
        self.assertEqual(artwork.bytes, ARTWORK_BYTES)
        self.assertEqual(artwork.mimetype, ARTWORK_MIMETYPE)

    @unittest_run_loop
    async def test_metadata_artwork_cache(self):
        self.usecase.example_video()
        self.usecase.change_artwork(ARTWORK_BYTES, ARTWORK_MIMETYPE, ARTWORK_ID)

        await self.playing(title="dummy")

        artwork = await self.atv.metadata.artwork()
        self.assertIsNotNone(artwork)
        self.assertEqual(artwork.bytes, ARTWORK_BYTES)

        artwork_id = self.atv.metadata.artwork_id

        # Change artwork data for same identifier (not really legal)
        self.usecase.change_artwork(ARTWORK_BYTES2, ARTWORK_MIMETYPE, ARTWORK_ID)

        # Expect previous data from cache
        artwork = await self.atv.metadata.artwork()
        self.assertIsNotNone(artwork)
        self.assertEqual(artwork.bytes, ARTWORK_BYTES)

        # Artwork identifier should be the same before as after
        self.assertEqual(self.atv.metadata.artwork_id, artwork_id)

    @unittest_run_loop
    async def test_push_updates(self):
        class PushListener:
            def __init__(self):
                self.playing = None

            def playstatus_update(self, updater, playstatus):
                _LOGGER.debug("Got playstatus: %s", playstatus)
                self.playing = playstatus

            @staticmethod
            def playstatus_error(updater, exception):
                pass

        # TODO: This test is a little weird as it leaks DMAP details
        # (revision). Should revise and make it better or use different tests
        # for each protocol.
        self.usecase.video_playing(
            paused=False, title="video1", total_time=40, position=10, revision=0
        )
        self.usecase.video_playing(
            paused=True, title="video2", total_time=30, position=20, revision=0
        )

        await self.playing()

        # Setup push updates which will instantly get the next one ("video2")
        listener = PushListener()
        self.atv.push_updater.listener = listener
        self.atv.push_updater.start()

        # Check that we got the right one
        await until(lambda: listener.playing and listener.playing.title == "video2")
        self.assertEqual(listener.playing.title, "video2")

    @unittest_run_loop
    async def test_push_updater_active(self):
        class DummyPushListener:
            @staticmethod
            def playstatus_update(updater, playstatus):
                pass

            @staticmethod
            def playstatus_error(updater, exception):
                pass

        self.usecase.video_playing(
            paused=False, title="video1", total_time=40, position=10, revision=0
        )

        self.assertFalse(self.atv.push_updater.active)

        listener = DummyPushListener()
        self.atv.push_updater.listener = listener
        self.atv.push_updater.start()
        self.assertTrue(self.atv.push_updater.active)

        self.atv.push_updater.stop()
        self.assertFalse(self.atv.push_updater.active)

    @unittest_run_loop
    async def test_metadata_artwork_none_if_not_available(self):
        self.usecase.example_video()
        self.usecase.change_artwork(b"", None)

        await self.playing(title="dummy")
        artwork = await self.atv.metadata.artwork()
        self.assertIsNone(artwork)

    @unittest_run_loop
    async def test_metadata_none_type_when_not_playing(self):
        self.usecase.nothing_playing()

        playing = await self.playing()
        self.assertEqual(playing.media_type, MediaType.Unknown)
        self.assertEqual(playing.device_state, DeviceState.Idle)

    @unittest_run_loop
    async def test_repeat_state(self):
        for repeat in RepeatState:
            self.usecase.example_video(repeat=repeat)
            playing = await self.playing(repeat=repeat)
            self.assertEqual(playing.repeat, repeat)

    @unittest_run_loop
    async def test_set_repeat(self):
        self.usecase.video_playing(
            paused=False, title="video", total_time=40, position=10
        )
        for repeat in RepeatState:
            await self.atv.remote_control.set_repeat(repeat)
            playing = await self.playing(repeat=repeat)
            self.assertEqual(playing.repeat, repeat)

    @unittest_run_loop
    async def test_shuffle_state_common(self):
        for shuffle in [ShuffleState.Off, ShuffleState.Songs]:
            self.usecase.example_video(shuffle=shuffle)
            playing = await self.playing(shuffle=shuffle)
            self.assertEqual(playing.shuffle, shuffle)

    @unittest_run_loop
    async def test_set_shuffle_common(self):
        self.usecase.example_video()

        for shuffle in [ShuffleState.Off, ShuffleState.Songs]:
            await self.atv.remote_control.set_shuffle(shuffle)
            playing = await self.playing(shuffle=shuffle)
            self.assertEqual(playing.shuffle, shuffle)

    @unittest_run_loop
    async def test_metadata_loading(self):
        self.usecase.media_is_loading()

        playing = await self.playing(device_state=DeviceState.Loading)
        self.assertEqual(playing.device_state, DeviceState.Loading)

    @unittest_run_loop
    async def test_metadata_seeking(self):
        self.usecase.example_video(paused=False, playback_rate=2.0)

        playing = await self.playing(title="dummy")
        self.assertEqual(playing.device_state, DeviceState.Seeking)

        self.usecase.example_video(paused=False, title="dummy2", playback_rate=1.0)
        playing = await self.playing(title="dummy2")
        self.assertEqual(playing.device_state, DeviceState.Playing)

        self.usecase.example_video(paused=False, title="dummy3", playback_rate=-1.0)
        playing = await self.playing(title="dummy3")
        self.assertEqual(playing.device_state, DeviceState.Seeking)

    @unittest_run_loop
    async def test_features_when_playing(self):
        feature_list = [
            FeatureName.Title,
            FeatureName.Artist,
            FeatureName.Album,
            FeatureName.Genre,
            FeatureName.TotalTime,
            FeatureName.Position,
        ]

        # At first, no feature is available
        self.usecase.nothing_playing()
        await self.playing()
        self.assertFeatures(FeatureState.Unavailable, *feature_list)

        # Play some music and all features should be available
        self.usecase.example_music()
        await self.playing(title="music")
        self.assertFeatures(FeatureState.Available, *feature_list)

    @unittest_run_loop
    async def test_features_play_url(self):
        # TODO: As availability is based on zeroconf properties, this test just
        # verifies that PlayUrl is available. It's hard to change zeroconf properties
        # between test runs here, so better tests will be written when dedicated
        # functional tests for AirPlay are written.
        self.assertFeatures(FeatureState.Available, FeatureName.PlayUrl)

    @unittest_run_loop
    async def test_playing_immutable(self):
        self.usecase.example_video()
        playing = await self.playing(title="dummy")

        # This is not allowed to modify "playing" instance above
        self.usecase.example_music()
        await self.playing(title="music")

        # Not a conclusive check but enough to cover the basic idea
        self.assertEqual(playing.title, "dummy")
        self.assertEqual(playing.total_time, 123)
        self.assertEqual(playing.position, 3)

    @unittest_run_loop
    async def test_volume_controls(self):
        controls = self.supported_volume_controls()

        self.assertFeatures(FeatureState.Unavailable, *controls)

        self.usecase.change_volume_control(available=False)
        self.usecase.example_video()
        await self.playing(title="dummy")

        self.assertFeatures(FeatureState.Unavailable, *controls)

        self.usecase.change_volume_control(available=True)
        self.usecase.example_video(title="dummy2")
        await self.playing(title="dummy2")

        self.assertFeatures(FeatureState.Available, *controls)

    # As DMAP is request based, volume control availability will not be automatically
    # updated when changed, i.e. it needs to be requested. This is the reason for
    # retrieving what is playing.
    @unittest_run_loop
    async def test_audio_volume_controls(self):
        self.usecase.change_volume_control(available=True)
        await self.atv.metadata.playing()

        await until(
            lambda: self.atv.features.in_state(
                FeatureState.Available, FeatureName.VolumeUp, FeatureName.VolumeDown
            )
        )

        await self.atv.audio.volume_up()
        await until(lambda: self.state.last_button_pressed == "volumeup")

        await self.atv.audio.volume_down()
        await until(lambda: self.state.last_button_pressed == "volumedown")
