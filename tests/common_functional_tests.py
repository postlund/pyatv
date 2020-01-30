"""Common functional tests for all protocols."""

import logging
import asyncio

from aiohttp.test_utils import (AioHTTPTestCase, unittest_run_loop)

import pyatv
from pyatv import exceptions, interface
from pyatv.const import (
    Protocol, MediaType, DeviceState, RepeatState, ShuffleState)
from pyatv.conf import AppleTV, AirPlayService
from tests import zeroconf_stub
from tests.utils import stub_sleep, until, faketime


_LOGGER = logging.getLogger(__name__)

ARTWORK_BYTES = b'1234'
ARTWORK_BYTES2 = b'4321'
ARTWORK_MIMETYPE = 'image/png'
ARTWORK_ID = 'artwork_id1'
EXAMPLE_STREAM = 'http://stream'

HOMESHARING_SERVICE_1 = zeroconf_stub.homesharing_service(
    'AAAA', b'Apple TV 1', '10.0.0.1', b'aaaa')
HOMESHARING_SERVICE_2 = zeroconf_stub.homesharing_service(
    'BBBB', b'Apple TV 2', '10.0.0.2', b'bbbb')


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

    async def get_application(self, loop=None):
        raise NotImplementedError()

    async def playing(self, **kwargs):
        return await until(
            poll, fn=self.atv.metadata.playing, **kwargs)

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
                conf, self.loop, protocol=Protocol.AirPlay)

    @unittest_run_loop
    async def test_pair_missing_service(self):
        conf = AppleTV('1.2.3.4', 'Apple TV')

        with self.assertRaises(exceptions.NoServiceError):
            await pyatv.pair(conf, Protocol.DMAP, self.loop)

    @unittest_run_loop
    async def test_play_url(self):
        self.usecase.airplay_playback_idle()
        self.usecase.airplay_playback_playing()
        self.usecase.airplay_playback_idle()

        await self.atv.stream.play_url(
            EXAMPLE_STREAM, port=self.server.port)

        self.assertEqual(self.fake_atv.last_airplay_url, EXAMPLE_STREAM)

    @unittest_run_loop
    async def test_play_url_not_authenticated_error(self):
        self.conf.get_service(Protocol.AirPlay).credentials = None
        self.usecase.airplay_require_authentication()

        with self.assertRaises(exceptions.AuthenticationError):
            await self.atv.stream.play_url(
                EXAMPLE_STREAM, port=self.server.port)

    @unittest_run_loop
    async def test_play_url_authenticated(self):
        self.usecase.airplay_require_authentication()
        self.usecase.airplay_playback_idle()
        self.usecase.airplay_playback_playing()
        self.usecase.airplay_playback_idle()

        await self.atv.stream.play_url(
            EXAMPLE_STREAM, port=self.server.port)

        self.assertEqual(self.fake_atv.last_airplay_url, EXAMPLE_STREAM)

    @unittest_run_loop
    async def test_button_up(self):
        await self.atv.remote_control.up()
        await until(lambda: self.fake_atv.last_button_pressed == 'up')

    @unittest_run_loop
    async def test_button_down(self):
        await self.atv.remote_control.down()
        await until(lambda: self.fake_atv.last_button_pressed == 'down')

    @unittest_run_loop
    async def test_button_left(self):
        await self.atv.remote_control.left()
        await until(lambda: self.fake_atv.last_button_pressed == 'left')

    @unittest_run_loop
    async def test_button_right(self):
        await self.atv.remote_control.right()
        await until(lambda: self.fake_atv.last_button_pressed == 'right')

    @unittest_run_loop
    async def test_button_select(self):
        await self.atv.remote_control.select()
        await until(lambda: self.fake_atv.last_button_pressed == 'select')

    @unittest_run_loop
    async def test_button_menu(self):
        await self.atv.remote_control.menu()
        await until(lambda: self.fake_atv.last_button_pressed == 'menu')

    @unittest_run_loop
    async def test_button_top_menu(self):
        await self.atv.remote_control.top_menu()
        await until(lambda: self.fake_atv.last_button_pressed == 'topmenu')

    @unittest_run_loop
    async def test_button_play(self):
        await self.atv.remote_control.play()
        await until(lambda: self.fake_atv.last_button_pressed == 'play')

    @unittest_run_loop
    async def test_button_pause(self):
        await self.atv.remote_control.pause()
        await until(lambda: self.fake_atv.last_button_pressed == 'pause')

    @unittest_run_loop
    async def test_button_stop(self):
        await self.atv.remote_control.stop()
        await until(lambda: self.fake_atv.last_button_pressed == 'stop')

    @unittest_run_loop
    async def test_button_next(self):
        await self.atv.remote_control.next()
        await until(lambda: self.fake_atv.last_button_pressed == 'nextitem')

    @unittest_run_loop
    async def test_button_previous(self):
        await self.atv.remote_control.previous()
        await until(lambda: self.fake_atv.last_button_pressed == 'previtem')

    def test_metadata_device_id(self):
        self.assertIn(self.atv.metadata.device_id, self.conf.all_identifiers)

    @unittest_run_loop
    async def test_close_connection(self):
        self.atv.listener = DummyDeviceListener()
        await self.atv.close()

        await asyncio.wait_for(
            self.atv.listener.closed_sem.acquire(), timeout=3.0)

    @unittest_run_loop
    async def test_metadata_video_paused(self):
        self.usecase.video_playing(paused=True, title='dummy',
                                   total_time=100, position=3)

        with faketime('pyatv', 0):
            playing = await self.playing(title='dummy')
            self.assertEqual(playing.media_type, MediaType.Video)
            self.assertEqual(playing.device_state, DeviceState.Paused)
            self.assertEqual(playing.title, 'dummy')
            self.assertEqual(playing.total_time, 100)
            self.assertEqual(playing.position, 3)

    @unittest_run_loop
    async def test_metadata_video_playing(self):
        self.usecase.video_playing(paused=False, title='video',
                                   total_time=40, position=10)

        with faketime('pyatv', 0):
            playing = await self.playing(title='video')
            self.assertEqual(playing.media_type, MediaType.Video)
            self.assertEqual(playing.device_state, DeviceState.Playing)
            self.assertEqual(playing.title, 'video')
            self.assertEqual(playing.total_time, 40)
            self.assertEqual(playing.position, 10)

    @unittest_run_loop
    async def test_metadata_music_paused(self):
        self.usecase.music_playing(paused=True, title='music',
                                   artist='artist', album='album',
                                   total_time=222, position=49,
                                   genre='genre')

        with faketime('pyatv', 0):
            playing = await self.playing(title='music')
            self.assertEqual(playing.media_type, MediaType.Music)
            self.assertEqual(playing.device_state, DeviceState.Paused)
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

        with faketime('pyatv', 0):
            playing = await self.playing(title='music')
            self.assertEqual(playing.media_type, MediaType.Music)
            self.assertEqual(playing.device_state, DeviceState.Playing)
            self.assertEqual(playing.title, 'music')
            self.assertEqual(playing.artist, 'test1')
            self.assertEqual(playing.album, 'test2')
            self.assertEqual(playing.genre, 'genre')
            self.assertEqual(playing.total_time, 2)
            self.assertEqual(playing.position, 1)

    @unittest_run_loop
    async def test_seek_in_playing_media(self):
        self.usecase.video_playing(paused=False, title='dummy',
                                   total_time=40, position=10)

        with faketime('pyatv', 0):
            await self.atv.remote_control.set_position(30)
            playing = await self.playing(position=30)
            self.assertEqual(playing.position, 30)

    @unittest_run_loop
    async def test_metadata_artwork(self):
        self.usecase.example_video()
        self.usecase.change_artwork(ARTWORK_BYTES, ARTWORK_MIMETYPE)

        await self.playing(title='dummy')
        artwork = await self.atv.metadata.artwork()
        self.assertIsNotNone(artwork)
        self.assertEqual(artwork.bytes, ARTWORK_BYTES)
        self.assertEqual(artwork.mimetype, ARTWORK_MIMETYPE)

    @unittest_run_loop
    async def test_metadata_artwork_cache(self):
        self.usecase.example_video()
        self.usecase.change_artwork(
            ARTWORK_BYTES, ARTWORK_MIMETYPE, ARTWORK_ID)

        await self.playing(title='dummy')

        artwork = await self.atv.metadata.artwork()
        self.assertIsNotNone(artwork)
        self.assertEqual(artwork.bytes, ARTWORK_BYTES)

        artwork_id = self.atv.metadata.artwork_id

        # Change artwork data for same identifier (not really legal)
        self.usecase.change_artwork(
            ARTWORK_BYTES2, ARTWORK_MIMETYPE, ARTWORK_ID)

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
                _LOGGER.debug('Got playstatus: %s', playstatus)
                self.playing = playstatus

            @staticmethod
            def playstatus_error(updater, exception):
                pass

        # TODO: This test is a little weird as it leaks DMAP details
        # (revision). Should revise and make it better or use different tests
        # for each protocol.
        self.usecase.video_playing(paused=False, title='video1',
                                   total_time=40, position=10,
                                   revision=0)
        self.usecase.video_playing(paused=True, title='video2',
                                   total_time=30, position=20,
                                   revision=0)

        await self.playing()

        # Setup push updates which will instantly get the next one ("video2")
        listener = PushListener()
        self.atv.push_updater.listener = listener
        self.atv.push_updater.start()

        # Check that we got the right one
        await until(lambda: listener.playing is not None)
        self.assertEqual(listener.playing.title, 'video2')

    @unittest_run_loop
    async def test_push_updater_active(self):

        class DummyPushListener:

            @staticmethod
            def playstatus_update(updater, playstatus):
                pass

            @staticmethod
            def playstatus_error(updater, exception):
                pass

        self.usecase.video_playing(paused=False, title='video1',
                                   total_time=40, position=10,
                                   revision=0)

        self.assertFalse(self.atv.push_updater.active)

        self.atv.push_updater.listener = DummyPushListener()
        self.atv.push_updater.start()
        self.assertTrue(self.atv.push_updater.active)

        self.atv.push_updater.stop()
        self.assertFalse(self.atv.push_updater.active)

    @unittest_run_loop
    async def test_metadata_artwork_none_if_not_available(self):
        self.usecase.example_video()
        self.usecase.change_artwork(b'', None)

        await self.playing(title='dummy')
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
        self.usecase.video_playing(paused=False, title='video',
                                   total_time=40, position=10)
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
