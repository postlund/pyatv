"""Test suit for pairing process with Apple TV."""

import asyncio
import asynctest
import ipaddress

from unittest.mock import patch
from pyatv import pairing, dmap, tag_definitions
from tests import zeroconf_stub, utils


REMOTE_NAME = 'pyatv remote'

# This is a valid config for default pairing guid
PIN_CODE = 1234
PAIRING_CODE = '690E6FF61E0D7C747654A42AED17047D'

# This is valid for a some other (non-default) config
PIN_CODE2 = 5555
PAIRING_GUID2 = '1234ABCDE56789FF'
PAIRING_CODE2 = '58AD1D195B6DAA58AA2EA29DC25B81C3'

PIN_CODE3 = 1
PAIRING_GUID3 = '7D1324235F535AE7'
PAIRING_CODE3 = 'A34C3361C7D57D61CA41F62A8042F069'

# Pairing guid is 8 bytes, which is 64 bits
RANDOM_128_BITS = 6558272190156386627
RANDOM_PAIRING_GUID = '5B03A9CF4A983143'


class PairingTest(asynctest.TestCase):

    @asyncio.coroutine
    def setUp(self):
        self.zeroconf = zeroconf_stub.stub(pairing)
        self.pairing = pairing.PairingHandler(
            self.loop, REMOTE_NAME, PIN_CODE,
            pairing_guid=pairing.DEFAULT_PAIRING_GUID)

        # TODO: currently stubs internal method, should provide stub
        # for netifaces later
        pairing._get_private_ip_addresses = \
            lambda: [ipaddress.ip_address('10.0.0.1')]

    @asyncio.coroutine
    def tearDown(self):
        yield from self.pairing.stop()

    def test_zeroconf_service_published(self):
        yield from self.pairing.start(self.zeroconf)

        self.assertEqual(len(self.zeroconf.registered_services), 1,
                         msg='no zeroconf service registered')

        service = self.zeroconf.registered_services[0]
        self.assertEqual(service.properties[b'DvNm'], REMOTE_NAME,
                         msg='remote name does not match')

    @patch('random.getrandbits')
    def test_random_pairing_guid_generated(self, getrandbits):
        getrandbits.return_value = RANDOM_128_BITS

        handler = pairing.PairingHandler(self.loop, REMOTE_NAME, PIN_CODE)

        self.assertEqual(handler.pairing_guid, RANDOM_PAIRING_GUID)

    def test_succesful_pairing(self):
        yield from self.pairing.start(self.zeroconf)

        url = self._pairing_url(PAIRING_CODE)
        data, _ = yield from utils.simple_get(url, self.loop)

        # Verify content returned in pairingresponse
        parsed = dmap.parse(data, tag_definitions.lookup_tag)
        self.assertEqual(dmap.first(parsed, 'cmpa', 'cmpg'), 1)
        self.assertEqual(dmap.first(parsed, 'cmpa', 'cmnm'), REMOTE_NAME)
        self.assertEqual(dmap.first(parsed, 'cmpa', 'cmty'), 'iPhone')

    def test_succesful_pairing_with_any_pin(self):
        self.pairing.pin_code = None
        yield from self.pairing.start(self.zeroconf)

        url = self._pairing_url('invalid_pairing_code')
        _, status = yield from utils.simple_get(url, self.loop)

        self.assertEqual(status, 200)

    def test_succesful_pairing_with_pin_leadering_zeros(self):
        self.pairing.pin_code = PIN_CODE3
        self.pairing.pairing_guid = PAIRING_GUID3
        yield from self.pairing.start(self.zeroconf)

        url = self._pairing_url(PAIRING_CODE3)
        _, status = yield from utils.simple_get(url, self.loop)

        self.assertEqual(status, 200)

    def test_pair_custom_pairing_guid(self):
        self.pairing.pin_code = PIN_CODE2
        self.pairing.pairing_guid = PAIRING_GUID2
        yield from self.pairing.start(self.zeroconf)

        url = self._pairing_url(PAIRING_CODE2)
        data, _ = yield from utils.simple_get(url, self.loop)

        # Verify content returned in pairingresponse
        parsed = dmap.parse(data, tag_definitions.lookup_tag)
        self.assertEqual(dmap.first(parsed, 'cmpa', 'cmpg'),
                         int(PAIRING_GUID2, 16))

    def test_failed_pairing(self):
        yield from self.pairing.start(self.zeroconf)

        url = self._pairing_url('wrong')
        _, status = yield from utils.simple_get(url, self.loop)

        self.assertEqual(status, 500)

    def _pairing_url(self, pairing_code):
        service = self.zeroconf.registered_services[0]
        server = 'http://127.0.0.1:{}'.format(service.port)
        return '{}/pairing?pairingcode={}&servicename=test'.format(
            server, pairing_code)
