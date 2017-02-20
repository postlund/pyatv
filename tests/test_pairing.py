"""Test suit for pairing process with Apple TV."""

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

    def test_succesful_pairing_with_device(self):
        zeroconf = zeroconf_stub.stub(pairing)

        handler = pairing.PairingHandler(self.loop, REMOTE_NAME, PIN_CODE)
        yield from handler.start(zeroconf)

        # Verify that bonjour service was published
        self.assertEqual(len(zeroconf.registered_services), 1,
                         msg='no zeroconf service registered')

        service = zeroconf.registered_services[0]
        self.assertEqual(service.properties[b'DvNm'], REMOTE_NAME,
                         msg='remote name does not match')

        # Extract port from service (as it is randomized) and request pairing
        # with the web server.
        server = 'http://127.0.0.1:{}'.format(service.port)
        url = '{}/pairing?pairingcode={}&servicename=test'.format(
            server, PAIRINGCODE)
        data = yield from utils.simple_get(self, url, self.loop)

        # Verify content returned in pairingresponse
        parsed = dmap.parse(data, tag_definitions.lookup_tag)
        self.assertEqual(dmap.first(parsed, 'cmpa', 'cmpg'), 1)
        self.assertEqual(dmap.first(parsed, 'cmpa', 'cmnm'), REMOTE_NAME)
        self.assertEqual(dmap.first(parsed, 'cmpa', 'cmty'), 'ipod')

        yield from handler.stop()
