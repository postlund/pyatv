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
    async def test_play_url_not_authenticated_error(self):
        self.conf.get_service(const.PROTOCOL_AIRPLAY).credentials = None
        self.usecase.airplay_require_authentication()

        with self.assertRaises(exceptions.AuthenticationError):
            await self.atv.airplay.play_url(
                AIRPLAY_STREAM, port=self.server.port)

    @unittest_run_loop
    async def test_play_url_authenticated(self):
        self.usecase.airplay_require_authentication()
        self.usecase.airplay_playback_idle()
        self.usecase.airplay_playback_playing()
        self.usecase.airplay_playback_idle()

        await self.atv.airplay.play_url(
            AIRPLAY_STREAM, port=self.server.port)

        self.assertEqual(self.fake_atv.last_airplay_url, AIRPLAY_STREAM)
