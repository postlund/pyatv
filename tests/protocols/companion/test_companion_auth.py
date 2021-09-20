"""Functional authentication tests with fake Companion Apple TV."""

import inspect
from ipaddress import IPv4Address

from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop

import pyatv
from pyatv import exceptions
from pyatv.conf import AppleTV, ManualService
from pyatv.const import Protocol
from pyatv.protocols.companion.server_auth import CLIENT_CREDENTIALS, PIN_CODE

from tests.fake_device import FakeAppleTV


class CompanionAuthFunctionalTest(AioHTTPTestCase):
    async def setUpAsync(self):
        self.service = ManualService(
            None, Protocol.Companion, self.fake_atv.get_port(Protocol.Companion), {}
        )
        self.conf = AppleTV(IPv4Address("127.0.0.1"), "Test device")
        self.conf.add_service(
            ManualService(
                "mrp_id", Protocol.MRP, self.fake_atv.get_port(Protocol.MRP), {}
            )
        )
        self.conf.add_service(self.service)

    async def tearDownAsync(self):
        await self.handle.close()
        await super().tearDownAsync()

    async def get_application(self, loop=None):
        self.fake_atv = FakeAppleTV(self.loop)
        self.fake_atv.add_service(Protocol.MRP)
        self.state, self.usecase = self.fake_atv.add_service(Protocol.Companion)
        return self.fake_atv.app

    @unittest_run_loop
    async def test_pairing_with_device(self):
        self.handle = await pyatv.pair(self.conf, Protocol.Companion, self.loop)

        self.assertIsNone(self.service.credentials)
        self.assertTrue(self.handle.device_provides_pin)

        await self.handle.begin()
        self.handle.pin(PIN_CODE)

        await self.handle.finish()

        self.assertTrue(self.handle.has_paired)
        self.assertTrue(self.state.has_paired)
        self.assertIsNotNone(self.service.credentials)

    @unittest_run_loop
    async def test_pairing_with_existing_credentials(self):
        self.service.credentials = CLIENT_CREDENTIALS

        self.handle = await pyatv.pair(self.conf, Protocol.Companion, self.loop)

        self.assertFalse(self.handle.has_paired)
        self.assertIsNotNone(self.service.credentials)
        self.assertTrue(self.handle.device_provides_pin)

        await self.handle.begin()
        self.handle.pin(PIN_CODE)

        await self.handle.finish()

        self.assertTrue(self.handle.has_paired)
        self.assertTrue(self.state.has_paired)
        self.assertIsNotNone(self.service.credentials)

    @unittest_run_loop
    async def test_pairing_no_pin(self):
        self.handle = await pyatv.pair(self.conf, Protocol.Companion, self.loop)

        await self.handle.begin()
        with self.assertRaises(exceptions.PairingError):
            await self.handle.finish()

    @unittest_run_loop
    async def test_pairing_with_bad_pin(self):
        self.handle = await pyatv.pair(self.conf, Protocol.Companion, self.loop)

        self.assertIsNone(self.service.credentials)
        self.assertTrue(self.handle.device_provides_pin)

        await self.handle.begin()
        self.handle.pin(PIN_CODE + 1)

        with self.assertRaises(exceptions.PairingError):
            await self.handle.finish()

        self.assertFalse(self.handle.has_paired)
        self.assertFalse(self.state.has_paired)
        self.assertIsNone(self.service.credentials)
