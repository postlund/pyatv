"""Functional pairing tests using the API with a fake DMAP Apple TV."""

import ipaddress

from aiohttp.test_utils import (AioHTTPTestCase, unittest_run_loop)

import pyatv
from pyatv.const import Protocol
from pyatv.conf import (DmapService, AppleTV)
from pyatv.dmap import pairing
from tests.dmap.fake_dmap_atv import (FakeAppleTV, AppleTVUseCases)
from tests import zeroconf_stub

HSGID = '12345-6789-0'
PAIRING_GUID = '0x0000000000000001'
SESSION_ID = 5555
REMOTE_NAME = 'pyatv remote'
PIN_CODE = 1234

# This is valid for the PAIR in the pairing module and pin 1234
# (extracted form a real device)
PAIRINGCODE = '690E6FF61E0D7C747654A42AED17047D'


class DmapPairFunctionalTest(AioHTTPTestCase):

    def setUp(self):
        AioHTTPTestCase.setUp(self)
        self.pairing = None

        self.service = DmapService(
            'dmap_id', PAIRING_GUID, port=self.server.port)
        self.conf = AppleTV('127.0.0.1', 'Apple TV')
        self.conf.add_service(self.service)

        # TODO: currently stubs internal method, should provide stub
        # for netifaces later
        pairing._get_private_ip_addresses = \
            lambda: [ipaddress.ip_address('10.0.0.1')]

        self.zeroconf = zeroconf_stub.stub(pyatv.dmap.pairing)

    async def tearDownAsync(self):
        await self.pairing.close()
        await super().tearDownAsync()

    async def get_application(self, loop=None):
        self.fake_atv = FakeAppleTV(
            HSGID, PAIRING_GUID, SESSION_ID, self)
        self.usecase = AppleTVUseCases(self.fake_atv)
        return self.fake_atv.app

    async def initiate_pairing(self,
                               name=REMOTE_NAME,
                               pairing_guid=PAIRING_GUID):
        self.usecase.pairing_response(REMOTE_NAME, PAIRINGCODE)

        options = {
            'zeroconf': self.zeroconf,
            'name': name,
            'pairing_guid': pairing_guid,
        }

        self.pairing = await pyatv.pair(
            self.conf, Protocol.DMAP, self.loop, **options)

    @unittest_run_loop
    async def test_pairing_with_device(self):
        await self.initiate_pairing()

        self.assertFalse(self.pairing.device_provides_pin)

        await self.pairing.begin()
        self.pairing.pin(PIN_CODE)

        await self.usecase.act_on_bonjour_services(self.zeroconf)

        await self.pairing.finish()

        self.assertTrue(self.pairing.has_paired)
        self.assertEqual(self.service.credentials, PAIRING_GUID)
