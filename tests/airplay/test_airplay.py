"""Functional tests for Airplay."""

from aiohttp import ClientSession
from aiohttp.test_utils import (AioHTTPTestCase, unittest_run_loop)

from pyatv import exceptions
from pyatv.airplay import player
from tests.airplay.fake_airplay_device import (
    FakeAirPlayDevice, AirPlayUseCases)


STREAM = 'http://airplaystream'
START_POSITION = 0.8


class AirPlayPlayerTest(AioHTTPTestCase):

    def setUp(self):
        AioHTTPTestCase.setUp(self)

        # This is a hack that overrides asyncio.sleep to avoid making the test
        # slow. It also counts number of calls, since this is quite important
        # to the general function.
        player.asyncio.sleep = self.fake_asyncio_sleep
        self.no_of_sleeps = 0

    async def get_application(self, loop=None):
        self.fake_device = FakeAirPlayDevice(self)
        self.usecase = AirPlayUseCases(self.fake_device)
        return self.fake_device.app

    async def fake_asyncio_sleep(self, time, loop):
        self.no_of_sleeps += 1

    @unittest_run_loop
    async def test_play_video(self):
        self.usecase.airplay_playback_idle()
        self.usecase.airplay_playback_playing()
        self.usecase.airplay_playback_idle()

        session = ClientSession(loop=self.loop)
        aplay = player.AirPlayPlayer(
            self.loop, session, '127.0.0.1', port=self.server.port)
        await aplay.play_url(STREAM, position=START_POSITION)

        self.assertEqual(self.fake_device.last_airplay_url, STREAM)
        self.assertEqual(self.fake_device.last_airplay_start, START_POSITION)
        self.assertIsNotNone(self.fake_device.last_airplay_uuid)
        self.assertEqual(self.no_of_sleeps, 2)  # playback + idle = 3

        await session.close()

    @unittest_run_loop
    async def test_play_video_no_permission(self):
        self.usecase.airplay_playback_playing_no_permission()

        session = ClientSession(loop=self.loop)
        aplay = player.AirPlayPlayer(
            self.loop, session, '127.0.0.1', port=self.server.port)

        with self.assertRaises(exceptions.NoCredentialsError):
            await aplay.play_url(STREAM, position=START_POSITION)
