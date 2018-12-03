"""Functional tests using the API with a fake Apple TV."""

import asyncio

from tests.log_output_handler import LogOutputHandler
from aiohttp import ClientSession
from aiohttp.test_utils import (AioHTTPTestCase, unittest_run_loop)

from pyatv import exceptions
from pyatv.airplay import player
from tests.fake_apple_tv import (FakeAppleTV, AppleTVUseCases)


STREAM = 'http://airplaystream'
START_POSITION = 0.8


class AirPlayPlayerTest(AioHTTPTestCase):

    def setUp(self):
        AioHTTPTestCase.setUp(self)
        self.log_handler = LogOutputHandler(self)
        self.session = ClientSession(loop=self.loop)

        # This is a hack that overrides asyncio.sleep to avoid making the test
        # slow. It also counts number of calls, since this is quite important
        # to the general function.
        player.asyncio.sleep = self.fake_asyncio_sleep
        self.no_of_sleeps = 0

    @asyncio.coroutine
    def tearDownAsync(self):
        self.log_handler.tearDown()
        yield from self.session.close()

    @asyncio.coroutine
    def get_application(self, loop=None):
        self.fake_atv = FakeAppleTV(self.loop, 0, 0, 0, self)
        self.usecase = AppleTVUseCases(self.fake_atv)
        return self.fake_atv

    @asyncio.coroutine
    def fake_asyncio_sleep(self, time, loop):
        self.no_of_sleeps += 1

    @unittest_run_loop
    def test_play_video(self):
        self.usecase.airplay_playback_idle()
        self.usecase.airplay_playback_playing()
        self.usecase.airplay_playback_idle()

        aplay = player.AirPlayPlayer(
            self.loop, self.session, '127.0.0.1', port=self.server.port)
        yield from aplay.play_url(STREAM, position=START_POSITION)

        self.assertEqual(self.fake_atv.last_airplay_url, STREAM)
        self.assertEqual(self.fake_atv.last_airplay_start, START_POSITION)
        self.assertEqual(self.no_of_sleeps, 2)  # playback + idle = 3

    @unittest_run_loop
    def test_play_video_no_permission(self):
        self.usecase.airplay_playback_playing_no_permission()

        aplay = player.AirPlayPlayer(
            self.loop, self.session, '127.0.0.1', port=self.server.port)

        with self.assertRaises(exceptions.NoCredentialsError):
            yield from aplay.play_url(STREAM, position=START_POSITION)
