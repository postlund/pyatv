"""AirPlay device authentication tests with fake device."""

import binascii

from aiohttp import ClientSession
from aiohttp.test_utils import (AioHTTPTestCase, unittest_run_loop)

from pyatv.airplay import srp
from pyatv.airplay.auth import (DeviceAuthenticator, AuthenticationVerifier)
from pyatv.exceptions import AuthenticationError
from pyatv.net import HttpSession
from tests.airplay.fake_airplay_device import (
    FakeAirPlayDevice, DEVICE_IDENTIFIER, DEVICE_AUTH_KEY, DEVICE_PIN)


INVALID_AUTH_KEY = binascii.unhexlify('0'*64)


class AirPlayAuthTest(AioHTTPTestCase):

    async def setUpAsync(self):
        self.session = ClientSession(loop=self.loop)

    async def tearDownAsync(self):
        await self.session.close()

    async def get_application(self, loop=None):
        self.fake_atv = FakeAirPlayDevice(self)
        return self.fake_atv.app

    @unittest_run_loop
    async def test_verify_invalid(self):
        http = HttpSession(
            self.session, 'http://127.0.0.1:{0}/'.format(self.server.port))
        handler = srp.SRPAuthHandler()
        handler.initialize(INVALID_AUTH_KEY)

        verifier = AuthenticationVerifier(http, handler)
        with self.assertRaises(AuthenticationError):
            await verifier.verify_authed()

    @unittest_run_loop
    async def test_verify_authenticated(self):
        http = HttpSession(
            self.session, 'http://127.0.0.1:{0}/'.format(self.server.port))
        handler = srp.SRPAuthHandler()
        handler.initialize(binascii.unhexlify(DEVICE_AUTH_KEY))

        verifier = AuthenticationVerifier(http, handler)
        self.assertTrue((await verifier.verify_authed()))

    @unittest_run_loop
    async def test_auth_successful(self):
        http = HttpSession(
            self.session, 'http://127.0.0.1:{0}/'.format(self.server.port))
        handler = srp.SRPAuthHandler()
        handler.initialize(INVALID_AUTH_KEY)

        auther = DeviceAuthenticator(http, handler)
        await auther.start_authentication()
        with self.assertRaises(AuthenticationError):
            await auther.finish_authentication(
                DEVICE_IDENTIFIER, DEVICE_PIN)

    @unittest_run_loop
    async def test_auth_failed(self):
        http = HttpSession(
            self.session, 'http://127.0.0.1:{0}/'.format(self.server.port))
        handler = srp.SRPAuthHandler()
        handler.initialize(binascii.unhexlify(DEVICE_AUTH_KEY))

        auther = DeviceAuthenticator(http, handler)
        await auther.start_authentication()
        self.assertTrue((await auther.finish_authentication(
            DEVICE_IDENTIFIER, DEVICE_PIN)))
