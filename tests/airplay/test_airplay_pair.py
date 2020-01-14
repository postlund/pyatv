"""Functional pairing tests using the API with a fake AirPlay Apple TV."""

import binascii
from asynctest.mock import patch

from aiohttp.test_utils import (AioHTTPTestCase, unittest_run_loop)

from pyatv import pair, exceptions
from pyatv.const import Protocol
from pyatv.conf import (AirPlayService, AppleTV)
from tests.airplay.fake_airplay_device import (
    FakeAirPlayDevice, AirPlayUseCases, DEVICE_CREDENTIALS, DEVICE_PIN,
    DEVICE_IDENTIFIER, DEVICE_AUTH_KEY)


def predetermined_key(num):
    """Return random data corresponding to hardcoded AirPlay keys."""
    if num == 8:
        return binascii.unhexlify(DEVICE_IDENTIFIER)
    return binascii.unhexlify(DEVICE_AUTH_KEY)


class PairFunctionalTest(AioHTTPTestCase):

    def setUp(self):
        AioHTTPTestCase.setUp(self)
        self.pairing = None

        self.service = AirPlayService(
            'airplay_id', port=self.server.port)
        self.conf = AppleTV('127.0.0.1', 'Apple TV')
        self.conf.add_service(self.service)

    async def tearDownAsync(self):
        await self.pairing.close()
        await super().tearDownAsync()

    async def get_application(self, loop=None):
        self.fake_atv = FakeAirPlayDevice(self)
        self.usecase = AirPlayUseCases(self.fake_atv)
        return self.fake_atv.app

    async def do_pairing(self, pin=DEVICE_PIN):
        self.usecase.airplay_require_authentication()

        self.pairing = await pair(
            self.conf, Protocol.AirPlay, self.loop)

        self.assertTrue(self.pairing.device_provides_pin)

        await self.pairing.begin()
        if pin:
            self.pairing.pin(pin)

        self.assertFalse(self.pairing.has_paired)

        await self.pairing.finish()
        self.assertTrue(self.pairing.has_paired)
        self.assertEqual(self.service.credentials, DEVICE_CREDENTIALS)

    @unittest_run_loop
    async def test_pairing_exception_invalid_pin(self):
        with self.assertRaises(exceptions.PairingError):
            await self.do_pairing(9999)

    @unittest_run_loop
    async def test_pairing_exception_no_pin(self):
        with self.assertRaises(exceptions.PairingError):
            await self.do_pairing(None)

    @unittest_run_loop
    @patch('os.urandom')
    async def test_pairing_with_device_new_credentials(self, rand_func):
        rand_func.side_effect = predetermined_key
        await self.do_pairing()

    @unittest_run_loop
    async def test_pairing_with_device_existing_credentials(self):
        self.conf.get_service(
            Protocol.AirPlay).credentials = DEVICE_CREDENTIALS
        await self.do_pairing()
