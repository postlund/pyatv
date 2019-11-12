"""Common functional tests for all protocols."""

import asyncio

from aiohttp.test_utils import (AioHTTPTestCase, unittest_run_loop)

import pyatv
from pyatv import const, exceptions
from pyatv.conf import AppleTV, AirPlayService
from tests import zeroconf_stub


EXPECTED_ARTWORK = b'1234'
AIRPLAY_STREAM = 'http://stream'

HOMESHARING_SERVICE_1 = zeroconf_stub.homesharing_service(
    'AAAA', b'Apple TV 1', '10.0.0.1', b'aaaa')
HOMESHARING_SERVICE_2 = zeroconf_stub.homesharing_service(
    'BBBB', b'Apple TV 2', '10.0.0.2', b'bbbb')


class CommonFunctionalTests(AioHTTPTestCase):

    def setUp(self):
        AioHTTPTestCase.setUp(self)

        # Make sleep calls do nothing to not slow down tests
        async def fake_sleep(self, time=None, loop=None):
            pass
        asyncio.sleep = fake_sleep

    async def get_application(self, loop=None):
        raise NotImplementedError()

    @unittest_run_loop
    async def test_connect_missing_device_id(self):
        conf = AppleTV('1.2.3.4', 'Apple TV')

        with self.assertRaises(exceptions.DeviceIdMissingError):
            await pyatv.connect(conf, self.loop)

    @unittest_run_loop
    async def test_connect_invalid_protocol(self):
        conf = AppleTV('1.2.3.4', 'Apple TV')
        conf.add_service(AirPlayService('airplay_id'))

        with self.assertRaises(exceptions.UnsupportedProtocolError):
            await pyatv.connect(
                conf, self.loop, protocol=const.PROTOCOL_AIRPLAY)

    @unittest_run_loop
    async def test_pair_missing_service(self):
        conf = AppleTV('1.2.3.4', 'Apple TV')

        with self.assertRaises(exceptions.NoServiceError):
            await pyatv.pair(conf, const.PROTOCOL_DMAP, self.loop)

    @unittest_run_loop
    async def test_play_url(self):
        self.usecase.airplay_playback_idle()
        self.usecase.airplay_playback_playing()
        self.usecase.airplay_playback_idle()

        await self.atv.airplay.play_url(
            AIRPLAY_STREAM, port=self.server.port)

        self.assertEqual(self.fake_atv.last_airplay_url, AIRPLAY_STREAM)

    @unittest_run_loop
    async def test_play_url_authenticated(self):
        self.usecase.airplay_require_authentication()
        self.usecase.airplay_playback_idle()
        self.usecase.airplay_playback_playing()
        self.usecase.airplay_playback_idle()

        await self.atv.airplay.play_url(
            AIRPLAY_STREAM, port=self.server.port)

        self.assertEqual(self.fake_atv.last_airplay_url, AIRPLAY_STREAM)

    @unittest_run_loop
    async def test_button_up(self):
        await self.atv.remote_control.up()
        self.assertEqual(self.fake_atv.buttons_press_count, 7)
        self.assertEqual(self.fake_atv.last_button_pressed, 'up')

    @unittest_run_loop
    async def test_button_down(self):
        await self.atv.remote_control.down()
        self.assertEqual(self.fake_atv.buttons_press_count, 7)
        self.assertEqual(self.fake_atv.last_button_pressed, 'down')

    @unittest_run_loop
    async def test_button_left(self):
        await self.atv.remote_control.left()
        self.assertEqual(self.fake_atv.buttons_press_count, 7)
        self.assertEqual(self.fake_atv.last_button_pressed, 'left')

    @unittest_run_loop
    async def test_button_right(self):
        await self.atv.remote_control.right()
        self.assertEqual(self.fake_atv.buttons_press_count, 7)
        self.assertEqual(self.fake_atv.last_button_pressed, 'right')

    @unittest_run_loop
    async def test_button_play(self):
        await self.atv.remote_control.play()
        self.assertEqual(self.fake_atv.last_button_pressed, 'play')

    @unittest_run_loop
    async def test_button_pause(self):
        await self.atv.remote_control.pause()
        self.assertEqual(self.fake_atv.last_button_pressed, 'pause')

    @unittest_run_loop
    async def test_button_stop(self):
        await self.atv.remote_control.stop()
        self.assertEqual(self.fake_atv.last_button_pressed, 'stop')

    @unittest_run_loop
    async def test_button_next(self):
        await self.atv.remote_control.next()
        self.assertEqual(self.fake_atv.last_button_pressed, 'nextitem')

    @unittest_run_loop
    async def test_button_previous(self):
        await self.atv.remote_control.previous()
        self.assertEqual(self.fake_atv.last_button_pressed, 'previtem')

    @unittest_run_loop
    async def test_button_select(self):
        await self.atv.remote_control.select()
        self.assertEqual(self.fake_atv.last_button_pressed, 'select')

    @unittest_run_loop
    async def test_button_menu(self):
        await self.atv.remote_control.menu()
        self.assertEqual(self.fake_atv.last_button_pressed, 'menu')

    @unittest_run_loop
    async def test_button_top_menu(self):
        await self.atv.remote_control.top_menu()
        self.assertEqual(self.fake_atv.last_button_pressed, 'topmenu')

    # TODO: This should check that device_id is one of the IDs
    #       passed to the services into the device.
    def test_metadata_device_id(self):
        self.assertEqual(self.atv.metadata.device_id, 'dmap_id')

    @unittest_run_loop
    async def test_metadata_artwork(self):
        self.usecase.change_artwork(EXPECTED_ARTWORK)

        artwork = await self.atv.metadata.artwork()
        self.assertEqual(artwork, EXPECTED_ARTWORK)

    @unittest_run_loop
    async def test_metadata_artwork_none_if_not_available(self):
        self.usecase.change_artwork(b'')

        artwork = await self.atv.metadata.artwork()
        self.assertIsNone(artwork)

    @unittest_run_loop
    async def test_metadata_none_type_when_not_playing(self):
        self.usecase.nothing_playing()

        playing = await self.atv.metadata.playing()
        self.assertEqual(playing.media_type, const.MEDIA_TYPE_UNKNOWN)
        self.assertEqual(playing.play_state, const.PLAY_STATE_NO_MEDIA)

    @unittest_run_loop
    async def test_metadata_video_paused(self):
        self.usecase.video_playing(paused=True, title='dummy',
                                   total_time=123, position=3)

        playing = await self.atv.metadata.playing()
        self.assertEqual(playing.media_type, const.MEDIA_TYPE_VIDEO)
        self.assertEqual(playing.play_state, const.PLAY_STATE_PAUSED)
        self.assertEqual(playing.title, 'dummy')
        self.assertEqual(playing.total_time, 123)
        self.assertEqual(playing.position, 3)

    @unittest_run_loop
    async def test_metadata_video_playing(self):
        self.usecase.video_playing(paused=False, title='video',
                                   total_time=40, position=10)

        playing = await self.atv.metadata.playing()
        self.assertEqual(playing.media_type, const.MEDIA_TYPE_VIDEO)
        self.assertEqual(playing.play_state, const.PLAY_STATE_PLAYING)
        self.assertEqual(playing.title, 'video')
        self.assertEqual(playing.total_time, 40)
        self.assertEqual(playing.position, 10)

    @unittest_run_loop
    async def test_metadata_music_paused(self):
        self.usecase.music_playing(paused=True, title='music',
                                   artist='artist', album='album',
                                   total_time=222, position=49,
                                   genre='genre')

        playing = await self.atv.metadata.playing()
        self.assertEqual(playing.media_type, const.MEDIA_TYPE_MUSIC)
        self.assertEqual(playing.play_state, const.PLAY_STATE_PAUSED)
        self.assertEqual(playing.title, 'music')
        self.assertEqual(playing.artist, 'artist')
        self.assertEqual(playing.album, 'album')
        self.assertEqual(playing.genre, 'genre')
        self.assertEqual(playing.total_time, 222)
        self.assertEqual(playing.position, 49)

    @unittest_run_loop
    async def test_metadata_music_playing(self):
        self.usecase.music_playing(paused=False, title='music',
                                   artist='test1', album='test2',
                                   total_time=2, position=1,
                                   genre='genre')

        playing = await self.atv.metadata.playing()
        self.assertEqual(playing.media_type, const.MEDIA_TYPE_MUSIC)
        self.assertEqual(playing.play_state, const.PLAY_STATE_PLAYING)
        self.assertEqual(playing.title, 'music')
        self.assertEqual(playing.artist, 'test1')
        self.assertEqual(playing.album, 'test2')
        self.assertEqual(playing.genre, 'genre')
        self.assertEqual(playing.total_time, 2)
        self.assertEqual(playing.position, 1)

    @unittest_run_loop
    async def test_push_updates(self):

        class PushListener:
            def __init__(self):
                self.playing = None

            def playstatus_update(self, updater, playstatus):
                self.playing = playstatus
                updater.stop()

            @staticmethod
            def playstatus_error(updater, exception):
                pass

        # Prepare two playstatus updates in the fake device. Take note: every
        # time start() is called, revision 0 should be used first. This will
        # make sure that we always get a push update instantly. Otherwise we
        # might hang and wait for an update.
        self.usecase.video_playing(paused=False, title='video1',
                                   total_time=40, position=10,
                                   revision=0)
        self.usecase.video_playing(paused=True, title='video2',
                                   total_time=30, position=20,
                                   revision=0)

        # Poll the first one ("video1")
        await self.atv.metadata.playing()

        # Setup push updates which will instantly get the next one ("video2")
        listener = PushListener()
        self.atv.push_updater.listener = listener
        await self.atv.push_updater.start()

        # Check that we got the right one
        self.assertIsNotNone(listener.playing)
        self.assertEqual(listener.playing.title, 'video2')

    @unittest_run_loop
    async def test_shuffle_state(self):
        self.usecase.example_video(shuffle=False)
        self.usecase.example_video(shuffle=True)

        playing = await self.atv.metadata.playing()
        self.assertFalse(playing.shuffle)

        playing = await self.atv.metadata.playing()
        self.assertTrue(playing.shuffle)

    @unittest_run_loop
    async def test_repeat_state(self):
        self.usecase.example_video(repeat=const.REPEAT_STATE_OFF)
        self.usecase.example_video(repeat=const.REPEAT_STATE_TRACK)
        self.usecase.example_video(repeat=const.REPEAT_STATE_ALL)

        playing = await self.atv.metadata.playing()
        self.assertEqual(playing.repeat, const.REPEAT_STATE_OFF)

        playing = await self.atv.metadata.playing()
        self.assertEqual(playing.repeat, const.REPEAT_STATE_TRACK)

        playing = await self.atv.metadata.playing()
        self.assertEqual(playing.repeat, const.REPEAT_STATE_ALL)

    @unittest_run_loop
    async def test_set_shuffle(self):
        await self.atv.remote_control.set_shuffle(1)
        self.assertEqual(self.fake_atv.properties['dacp.shufflestate'], 1)

        await self.atv.remote_control.set_shuffle(0)
        self.assertEqual(self.fake_atv.properties['dacp.shufflestate'], 0)

    @unittest_run_loop
    async def test_set_repeat(self):
        await self.atv.remote_control.set_repeat(1)
        self.assertEqual(self.fake_atv.properties['dacp.repeatstate'], 1)

        await self.atv.remote_control.set_repeat(2)
        self.assertEqual(self.fake_atv.properties['dacp.repeatstate'], 2)

    @unittest_run_loop
    async def test_seek_in_playing_media(self):
        await self.atv.remote_control.set_position(60)
        self.assertEqual(self.fake_atv.properties['dacp.playingtime'], 60000)

    @unittest_run_loop
    async def test_metadata_loading(self):
        self.usecase.media_is_loading()

        playing = await self.atv.metadata.playing()
        self.assertEqual(playing.play_state, const.PLAY_STATE_LOADING)
