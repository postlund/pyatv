"""AirPlay device authentication tests with fake Apple TV."""

import asyncio
import binascii

from tests.log_output_handler import LogOutputHandler
from aiohttp import ClientSession
from aiohttp.test_utils import (AioHTTPTestCase, unittest_run_loop)

from pyatv.airplay import srp
from pyatv.airplay.auth import (DeviceAuthenticator, AuthenticationVerifier)
from pyatv.exceptions import DeviceAuthenticationError
from pyatv.net import HttpSession
from tests.fake_apple_tv import (
    FakeAppleTV, DEVICE_IDENTIFIER, DEVICE_AUTH_KEY, DEVICE_PIN)


INVALID_AUTH_KEY = binascii.unhexlify('0'*64)


class AirPlayPlayerTest(AioHTTPTestCase):

    def setUp(self):
        AioHTTPTestCase.setUp(self)
        self.log_handler = LogOutputHandler(self)
        self.session = ClientSession(loop=self.loop)

    def tearDown(self):
        self.session.close()
        self.log_handler.tearDown()
        AioHTTPTestCase.tearDown(self)

    @asyncio.coroutine
    def get_application(self, loop=None):
        self.fake_atv = FakeAppleTV(self.loop, 0, 0, 0, self)

        # Import TestServer here and not globally, otherwise py.test will
        # complain when running:
        #
        #   test_functional.py cannot collect test class 'TestServer'
        #   because it has a __init__ constructor
        from aiohttp.test_utils import TestServer
        return TestServer(self.fake_atv)

    @unittest_run_loop
    def test_verify_invalid(self):
        http = HttpSession(
            self.session, 'http://127.0.0.1:{0}/'.format(self.app.port))
        handler = srp.SRPAuthHandler()
        handler.initialize(INVALID_AUTH_KEY)

        verifier = AuthenticationVerifier(http, handler)
        with self.assertRaises(DeviceAuthenticationError):
            yield from verifier.verify_authed()

    @unittest_run_loop
    def test_verify_authenticated(self):
        http = HttpSession(
            self.session, 'http://127.0.0.1:{0}/'.format(self.app.port))
        handler = srp.SRPAuthHandler()
        handler.initialize(binascii.unhexlify(DEVICE_AUTH_KEY))

        verifier = AuthenticationVerifier(http, handler)
        self.assertTrue((yield from verifier.verify_authed()))

    @unittest_run_loop
    def test_auth_successful(self):
        http = HttpSession(
            self.session, 'http://127.0.0.1:{0}/'.format(self.app.port))
        handler = srp.SRPAuthHandler()
        handler.initialize(INVALID_AUTH_KEY)

        auther = DeviceAuthenticator(http, handler)
        yield from auther.start_authentication()
        with self.assertRaises(DeviceAuthenticationError):
            yield from auther.finish_authentication(
                DEVICE_IDENTIFIER, DEVICE_PIN)

    @unittest_run_loop
    def test_auth_failed(self):
        http = HttpSession(
            self.session, 'http://127.0.0.1:{0}/'.format(self.app.port))
        handler = srp.SRPAuthHandler()
        handler.initialize(binascii.unhexlify(DEVICE_AUTH_KEY))

        auther = DeviceAuthenticator(http, handler)
        yield from auther.start_authentication()
        self.assertTrue((yield from auther.finish_authentication(
            DEVICE_IDENTIFIER, DEVICE_PIN)))
