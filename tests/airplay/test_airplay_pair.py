"""Functional pairing tests using the API with a fake AirPlay Apple TV."""

from aiohttp.test_utils import (AioHTTPTestCase, unittest_run_loop)

import pyatv
from pyatv import const
from pyatv.conf import (AirPlayService, AppleTV)
from tests.airplay.fake_airplay_device import (
    FakeAirPlayDevice, AirPlayUseCases, DEVICE_CREDENTIALS, DEVICE_PIN)


class PairFunctionalTest(AioHTTPTestCase):

    def setUp(self):
        AioHTTPTestCase.setUp(self)
        self.pairing = None

        self.service = AirPlayService(
            'airplay_id', credentials=DEVICE_CREDENTIALS,
            port=self.server.port)
        self.conf = AppleTV('127.0.0.1', 'Apple TV')
        self.conf.add_service(self.service)

    async def tearDownAsync(self):
        await self.pairing.close()
        await super().tearDownAsync()

    async def get_application(self, loop=None):
        self.fake_atv = FakeAirPlayDevice(self)
        self.usecase = AirPlayUseCases(self.fake_atv)
        return self.fake_atv.app

    async def initiate_pairing(self):
        self.usecase.airplay_require_authentication()

        options = {}

        self.pairing = await pyatv.pair(
            self.conf, const.PROTOCOL_AIRPLAY, self.loop, **options)

    @unittest_run_loop
    async def test_pairing_with_device(self):
        await self.initiate_pairing()

        self.assertTrue(self.pairing.device_provides_pin)

        await self.pairing.begin()
        self.pairing.pin(DEVICE_PIN)

        self.assertFalse(self.pairing.has_paired)

        await self.pairing.finish()
        self.assertTrue(self.pairing.has_paired)
        self.assertEqual(self.service.credentials, DEVICE_CREDENTIALS)
