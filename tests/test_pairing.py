"""Test suit for pairing process with Apple TV."""

import asyncio
import asynctest

from pyatv import pairing, dmap, tag_definitions
from tests import zeroconf_stub, utils


REMOTE_NAME = 'pyatv remote'
PIN_CODE = 1234
PAIRING_GUID = '0x0000000000000001'

# This is valid for the PAIRING_GUID and PIN_CODE. Verified with a real
# real device.
PAIRINGCODE = '690E6FF61E0D7C747654A42AED17047D'


class PairingTest(asynctest.TestCase):

    @asyncio.coroutine
    def setUp(self):
        self.zeroconf = zeroconf_stub.stub(pairing)
        self.pairing = pairing.PairingHandler(self.loop, REMOTE_NAME, PIN_CODE)
        yield from self.pairing.start(self.zeroconf)

    @asyncio.coroutine
    def tearDown(self):
        yield from self.pairing.stop()

    def test_zeroconf_service_published(self):
        self.assertEqual(len(self.zeroconf.registered_services), 1,
                         msg='no zeroconf service registered')

        service = self.zeroconf.registered_services[0]
        self.assertEqual(service.properties[b'DvNm'], REMOTE_NAME,
                         msg='remote name does not match')

    def test_succesful_pairing(self):
        url = self._pairing_url(PAIRINGCODE)
        data, _ = yield from utils.simple_get(url, self.loop)

        # Verify content returned in pairingresponse
        parsed = dmap.parse(data, tag_definitions.lookup_tag)
        self.assertEqual(dmap.first(parsed, 'cmpa', 'cmpg'), 1)
        self.assertEqual(dmap.first(parsed, 'cmpa', 'cmnm'), REMOTE_NAME)
        self.assertEqual(dmap.first(parsed, 'cmpa', 'cmty'), 'ipod')

    def test_failed_pairing(self):
        url = self._pairing_url('wrong')
        _, status = yield from utils.simple_get(url, self.loop)

        self.assertEqual(status, 500)

    def _pairing_url(self, pairing_code):
        service = self.zeroconf.registered_services[0]
        server = 'http://127.0.0.1:{}'.format(service.port)
        return '{}/pairing?pairingcode={}&servicename=test'.format(
            server, pairing_code)
