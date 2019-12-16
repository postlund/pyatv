"""Functional tests for Airplay."""

from aiohttp import ClientSession
from aiohttp.test_utils import (AioHTTPTestCase, unittest_run_loop)

from pyatv import exceptions, net
from pyatv.airplay import player
from tests.airplay.fake_airplay_device import (
    FakeAirPlayDevice, AirPlayUseCases)


STREAM = 'http://airplaystream'
START_POSITION = 0.8


class AirPlayPlayerTest(AioHTTPTestCase):

    async def setUpAsync(self):
        await AioHTTPTestCase.setUpAsync(self)

        # This is a hack that overrides asyncio.sleep to avoid making the test
        # slow. It also counts number of calls, since this is quite important
        # to the general function.
        player.asyncio.sleep = self.fake_asyncio_sleep
        self.no_of_sleeps = 0

        self.session = ClientSession(loop=self.loop)
        http = net.HttpSession(
          self.session, 'http://127.0.0.1:{0}/'.format(self.server.port))
        self.player = player.AirPlayPlayer(self.loop, http)

    async def tearDownAsync(self):
        await AioHTTPTestCase.tearDownAsync(self)
        await self.session.close()

    async def get_application(self, loop=None):
        self.fake_device = FakeAirPlayDevice(self)
        self.usecase = AirPlayUseCases(self.fake_device)
        return self.fake_device.app

    async def fake_asyncio_sleep(self, time, loop=None):
        self.no_of_sleeps += 1

    @unittest_run_loop
    async def test_play_video(self):
        self.usecase.airplay_playback_idle()
        self.usecase.airplay_playback_playing()
        self.usecase.airplay_playback_idle()

        await self.player.play_url(STREAM, position=START_POSITION)

        self.assertEqual(self.fake_device.last_airplay_url, STREAM)
        self.assertEqual(self.fake_device.last_airplay_start, START_POSITION)
        self.assertIsNotNone(self.fake_device.last_airplay_uuid)
        self.assertEqual(self.no_of_sleeps, 2)  # playback + idle = 3

    @unittest_run_loop
    async def test_play_video_no_permission(self):
        self.usecase.airplay_playback_playing_no_permission()

        with self.assertRaises(exceptions.NoCredentialsError):
            await self.player.play_url(STREAM, position=START_POSITION)

    @unittest_run_loop
    async def test_play_with_retries(self):
        self.usecase.airplay_play_failure(2)
        self.usecase.airplay_playback_playing()
        self.usecase.airplay_playback_idle()

        await self.player.play_url(STREAM, position=START_POSITION)

        self.assertEqual(
            self.fake_device.play_count, 3)  # Two retries + success

    @unittest_run_loop
    async def test_play_with_too_many_retries(self):
        self.usecase.airplay_play_failure(10)
        self.usecase.airplay_playback_playing()
        self.usecase.airplay_playback_idle()

        with self.assertRaises(exceptions.PlaybackError):
            await self.player.play_url(STREAM, position=START_POSITION)
