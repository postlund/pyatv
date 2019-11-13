"""Functional tests using the API with a fake DMAP Apple TV."""

import ipaddress

from aiohttp.test_utils import unittest_run_loop

import pyatv
from pyatv import exceptions
from pyatv.conf import (AirPlayService, DmapService, AppleTV)
from pyatv.dmap import pairing
from tests.dmap.fake_dmap_atv import (FakeAppleTV, AppleTVUseCases)
from tests.airplay.fake_airplay_device import DEVICE_CREDENTIALS
from tests import (zeroconf_stub, common_functional_tests)

HSGID = '12345-6789-0'
PAIRING_GUID = '0x0000000000000001'
SESSION_ID = 55555
REMOTE_NAME = 'pyatv remote'
PIN_CODE = 1234

EXPECTED_ARTWORK = b'1234'
AIRPLAY_STREAM = 'http://stream'

# This is valid for the PAIR in the pairing module and pin 1234
# (extracted form a real device)
PAIRINGCODE = '690E6FF61E0D7C747654A42AED17047D'

HOMESHARING_SERVICE_1 = zeroconf_stub.homesharing_service(
    'AAAA', b'Apple TV 1', '10.0.0.1', b'aaaa')
HOMESHARING_SERVICE_2 = zeroconf_stub.homesharing_service(
    'BBBB', b'Apple TV 2', '10.0.0.2', b'bbbb')


class DMAPFunctionalTest(common_functional_tests.CommonFunctionalTests):

    async def setUpAsync(self):
        await super().setUpAsync()
        self.atv = await self.get_connected_device(HSGID)

        # TODO: currently stubs internal method, should provide stub
        # for netifaces later
        pairing._get_private_ip_addresses = \
            lambda: [ipaddress.ip_address('10.0.0.1')]

    async def tearDownAsync(self):
        await self.atv.close()
        await super().tearDownAsync()

    async def get_application(self, loop=None):
        self.fake_atv = FakeAppleTV(
            HSGID, PAIRING_GUID, SESSION_ID, self)
        self.usecase = AppleTVUseCases(self.fake_atv)
        return self.fake_atv.app

    async def get_connected_device(self, hsgid):
        self.dmap_service = DmapService(
            'dmap_id', hsgid, port=self.server.port)
        self.airplay_service = AirPlayService(
            'airplay_id', self.server.port, DEVICE_CREDENTIALS)
        self.conf = AppleTV('127.0.0.1', 'Apple TV')
        self.conf.add_service(self.dmap_service)
        self.conf.add_service(self.airplay_service)
        return await pyatv.connect(self.conf, self.loop)

    @unittest_run_loop
    async def test_not_supportedt(self):
        with self.assertRaises(exceptions.NotSupportedError):
            await self.atv.remote_control.suspend()

    @unittest_run_loop
    async def test_connect_failed(self):
        # Twice since the client will retry one time
        self.usecase.make_login_fail()
        self.usecase.make_login_fail()

        with self.assertRaises(exceptions.AuthenticationError):
            await self.atv.connect()

    # This test verifies issue #2 (automatic re-login). It uses the artwork
    # API, but it could have been any API since the login code is the same.
    @unittest_run_loop
    async def test_relogin_if_session_expired(self):
        await self.atv.connect()

        # Here, we are logged in and currently have a asession id. These
        # usescases will result in being logged out (HTTP 403) and forcing a
        # re-login with a new session id (1234)
        self.usecase.force_relogin(1234)
        self.usecase.artwork_no_permission()
        self.usecase.change_artwork(EXPECTED_ARTWORK)

        artwork = await self.atv.metadata.artwork()
        self.assertEqual(artwork, EXPECTED_ARTWORK)

    @unittest_run_loop
    async def test_login_with_hsgid_succeed(self):
        session_id = await self.atv.connect()
        self.assertEqual(SESSION_ID, session_id)

    @unittest_run_loop
    async def test_login_with_pairing_guid_succeed(self):
        await self.atv.close()
        self.atv = await self.get_connected_device(PAIRING_GUID)
        session_id = await self.atv.connect()
        self.assertEqual(SESSION_ID, session_id)
