"""AirPlay device authentication tests with fake device."""

import binascii

from aiohttp import ClientSession
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop

from pyatv.const import Protocol
from pyatv.airplay import srp
from pyatv.airplay.auth import DeviceAuthenticator, AuthenticationVerifier
from pyatv.exceptions import AuthenticationError
from pyatv.support.net import HttpSession
from tests.fake_device import FakeAppleTV
from tests.fake_device.airplay import (
    DEVICE_IDENTIFIER,
    DEVICE_AUTH_KEY,
    DEVICE_PIN,
)


INVALID_AUTH_KEY = binascii.unhexlify("0" * 64)


class AirPlayAuthTest(AioHTTPTestCase):
    async def setUpAsync(self):
        self.session = ClientSession()

    async def tearDownAsync(self):
        await self.session.close()

    async def get_application(self, loop=None):
        self.fake_atv = FakeAppleTV(self.loop)
        self.fake_atv.add_service(Protocol.AirPlay)
        return self.fake_atv.app

    @unittest_run_loop
    async def test_verify_invalid(self):
        http = HttpSession(
            self.session, "http://127.0.0.1:{0}/".format(self.server.port)
        )
        handler = srp.SRPAuthHandler()
        handler.initialize(INVALID_AUTH_KEY)

        verifier = AuthenticationVerifier(http, handler)
        with self.assertRaises(AuthenticationError):
            await verifier.verify_authed()

    @unittest_run_loop
    async def test_verify_authenticated(self):
        http = HttpSession(
            self.session, "http://127.0.0.1:{0}/".format(self.server.port)
        )
        handler = srp.SRPAuthHandler()
        handler.initialize(binascii.unhexlify(DEVICE_AUTH_KEY))

        verifier = AuthenticationVerifier(http, handler)
        self.assertTrue((await verifier.verify_authed()))

    @unittest_run_loop
    async def test_auth_failed(self):
        http = HttpSession(
            self.session, "http://127.0.0.1:{0}/".format(self.server.port)
        )
        handler = srp.SRPAuthHandler()
        handler.initialize(INVALID_AUTH_KEY)

        authenticator = DeviceAuthenticator(http, handler)
        await authenticator.start_authentication()
        with self.assertRaises(AuthenticationError):
            await authenticator.finish_authentication(DEVICE_IDENTIFIER, DEVICE_PIN)

    @unittest_run_loop
    async def test_auth_successful(self):
        http = HttpSession(
            self.session, "http://127.0.0.1:{0}/".format(self.server.port)
        )
        handler = srp.SRPAuthHandler()
        handler.initialize(binascii.unhexlify(DEVICE_AUTH_KEY))

        authenticator = DeviceAuthenticator(http, handler)
        await authenticator.start_authentication()
        self.assertTrue(
            (await authenticator.finish_authentication(DEVICE_IDENTIFIER, DEVICE_PIN))
        )
