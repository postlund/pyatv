"""Functional tests using the API with a fake Apple TV."""

import asyncio

from tests.log_output_handler import LogOutputHandler
from aiohttp import ClientSession
from aiohttp.test_utils import (AioHTTPTestCase, unittest_run_loop)

from pyatv import airplay
from tests.fake_apple_tv import (FakeAppleTV, AppleTVUseCases)


STREAM = 'http://airplaystream'
START_POSITION = 0.8


class AirPlayTest(AioHTTPTestCase):

    def setUp(self):
        AioHTTPTestCase.setUp(self)
        self.log_handler = LogOutputHandler(self)

        # This is a hack that overrides asyncio.sleep to avoid making the test
        # slow. It also counts number of calls, since this is quite important
        # to the general function.
        airplay.asyncio.sleep = self.fake_asyncio_sleep
        self.no_of_sleeps = 0

    def tearDown(self):
        AioHTTPTestCase.tearDown(self)
        self.log_handler.tearDown()

    def get_app(self, loop):
        self.fake_atv = FakeAppleTV(loop, 0, 0, 0, self)
        self.usecase = AppleTVUseCases(self.fake_atv)

        # Import TestServer here and not globally, otherwise py.test will
        # complain when running:
        #
        #   test_functional.py cannot collect test class 'TestServer'
        #   because it has a __init__ constructor
        from aiohttp.test_utils import TestServer
        return TestServer(self.fake_atv)

    @asyncio.coroutine
    def fake_asyncio_sleep(self, time, loop):
        self.no_of_sleeps += 1

    @unittest_run_loop
    def test_play_video(self):
        self.usecase.airplay_playback_idle()
        self.usecase.airplay_playback_playing()
        self.usecase.airplay_playback_idle()

        session = ClientSession(loop=self.loop)
        aplay = airplay.AirPlay(self.loop, session, '127.0.0.1')
        yield from aplay.play_url(STREAM, START_POSITION, self.app.port)

        self.assertEqual(self.fake_atv.last_airplay_url, STREAM)
        self.assertEqual(self.fake_atv.last_airplay_start, START_POSITION)
        self.assertEqual(self.no_of_sleeps, 2)  # playback + idle = 3

        yield from session.close()
