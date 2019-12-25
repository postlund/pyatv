"""Common functional tests for all protocols."""

from aiohttp.test_utils import (AioHTTPTestCase, unittest_run_loop)

import pyatv
from pyatv import exceptions
from pyatv.const import Protocol, MediaType, DeviceState
from pyatv.conf import AppleTV, AirPlayService
from tests import zeroconf_stub
from tests.utils import stub_sleep, until


EXPECTED_ARTWORK = b'1234'
AirPlay_STREAM = 'http://stream'

HOMESHARING_SERVICE_1 = zeroconf_stub.homesharing_service(
    'AAAA', b'Apple TV 1', '10.0.0.1', b'aaaa')
HOMESHARING_SERVICE_2 = zeroconf_stub.homesharing_service(
    'BBBB', b'Apple TV 2', '10.0.0.2', b'bbbb')


async def poll(fn, **kwargs):
    result = await fn()
    conds = [getattr(result, f) == val for f, val in kwargs.items()]
    return all(conds), result


class CommonFunctionalTests(AioHTTPTestCase):

    def setUp(self):
        AioHTTPTestCase.setUp(self)
        stub_sleep()

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

        await self.atv.airplay.play_url(
            AirPlay_STREAM, port=self.server.port)

        self.assertEqual(self.fake_atv.last_airplay_url, AirPlay_STREAM)

    @unittest_run_loop
    async def test_play_url_not_authenticated_error(self):
        self.conf.get_service(Protocol.AirPlay).credentials = None
        self.usecase.airplay_require_authentication()

        with self.assertRaises(exceptions.AuthenticationError):
            await self.atv.airplay.play_url(
                AirPlay_STREAM, port=self.server.port)

    @unittest_run_loop
    async def test_play_url_authenticated(self):
        self.usecase.airplay_require_authentication()
        self.usecase.airplay_playback_idle()
        self.usecase.airplay_playback_playing()
        self.usecase.airplay_playback_idle()

        await self.atv.airplay.play_url(
            AirPlay_STREAM, port=self.server.port)

        self.assertEqual(self.fake_atv.last_airplay_url, AirPlay_STREAM)

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

    @unittest_run_loop
    async def test_metadata_video_paused(self):
        self.usecase.video_playing(paused=True, title='dummy',
                                   total_time=123, position=3)

        playing = await until(
            poll, fn=self.atv.metadata.playing, title='dummy')
        self.assertEqual(playing.media_type, MediaType.Video)
        self.assertEqual(playing.device_state, DeviceState.Paused)
        self.assertEqual(playing.title, 'dummy')
        self.assertEqual(playing.total_time, 123)
        self.assertEqual(playing.position, 3)
