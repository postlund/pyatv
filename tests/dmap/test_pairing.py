"""Test suit for pairing process with Apple TV."""

import asynctest
import ipaddress

from pyatv import conf
from pyatv.dmap import (pairing, parser, tag_definitions)
from tests import zeroconf_stub, utils


REMOTE_NAME = 'pyatv remote'

# This is a valid config for default pairing guid
PIN_CODE = 1234
PAIRING_GUID = '0x0000000000000001'
PAIRING_CODE = '690E6FF61E0D7C747654A42AED17047D'

# This is valid for a some other (non-default) config
PIN_CODE2 = 5555
PAIRING_GUID2 = '0x1234ABCDE56789FF'
PAIRING_CODE2 = '58AD1D195B6DAA58AA2EA29DC25B81C3'

# Code is padded with zeros
PIN_CODE3 = 1
PAIRING_GUID3 = '0x7D1324235F535AE7'
PAIRING_CODE3 = 'A34C3361C7D57D61CA41F62A8042F069'

# Pairing guid is 8 bytes, which is 64 bits
RANDOM_128_BITS = 6558272190156386627
RANDOM_PAIRING_GUID = '0x5B03A9CF4A983143'
RANDOM_PAIRING_CODE = '7AF2D0B8629DE3C704D40A14C9E8CB93'


class PairingTest(asynctest.TestCase):

    async def setUp(self):
        self.service = conf.DmapService(None, None)
        self.config = conf.AppleTV('Apple TV', '127.0.0.1')
        self.config.add_service(self.service)
        self.zeroconf = zeroconf_stub.stub(pairing)
        self.pairing = None

        # TODO: currently stubs internal method, should provide stub
        # for netifaces later
        pairing._get_private_ip_addresses = \
            lambda: [ipaddress.ip_address('10.0.0.1')]

    async def tearDown(self):
        await self.pairing.finish()

    async def _start(self,
                     pin_code=PIN_CODE,
                     pairing_guid=PAIRING_GUID,
                     name=REMOTE_NAME):
        options = {'zeroconf': self.zeroconf}
        if pairing_guid:
            options['pairing_guid'] = pairing_guid
        if name:
            options['name'] = name

        self.pairing = pairing.DmapPairingHandler(
            self.config, None, self.loop, **options)
        await self.pairing.begin()
        self.pairing.pin(pin_code)

    async def test_zeroconf_service_published(self):
        await self._start()

        self.assertEqual(len(self.zeroconf.registered_services), 1,
                         msg='no zeroconf service registered')

        service = self.zeroconf.registered_services[0]
        self.assertEqual(service.properties[b'DvNm'], REMOTE_NAME,
                         msg='remote name does not match')

    async def test_succesful_pairing(self):
        await self._start()

        url = self._pairing_url(PAIRING_CODE)
        data, _ = await utils.simple_get(url)

        await self.pairing.finish()

        # Verify content returned in pairingresponse
        parsed = parser.parse(data, tag_definitions.lookup_tag)
        self.assertEqual(parser.first(parsed, 'cmpa', 'cmpg'), 1)
        self.assertEqual(parser.first(parsed, 'cmpa', 'cmnm'), REMOTE_NAME)
        self.assertEqual(parser.first(parsed, 'cmpa', 'cmty'), 'iPhone')

        self.assertEqual(self.service.credentials, PAIRING_GUID)

    async def test_successful_pairing_random_pairing_guid_generated(self):
        pairing.random.getrandbits = lambda x: RANDOM_128_BITS

        await self._start(pairing_guid=None)

        url = self._pairing_url(RANDOM_PAIRING_CODE)
        await utils.simple_get(url)

        await self.pairing.finish()

        self.assertEqual(self.service.credentials, RANDOM_PAIRING_GUID)

    async def test_succesful_pairing_with_any_pin(self):
        await self._start(pin_code=None)

        url = self._pairing_url('invalid_pairing_code')
        _, status = await utils.simple_get(url)

        self.assertEqual(status, 200)

    async def test_succesful_pairing_with_pin_leadering_zeros(self):
        await self._start(pin_code=PIN_CODE3, pairing_guid=PAIRING_GUID3)

        url = self._pairing_url(PAIRING_CODE3)
        _, status = await utils.simple_get(url)

        self.assertEqual(status, 200)

    async def test_pair_custom_pairing_guid(self):
        await self._start(pin_code=PIN_CODE2, pairing_guid=PAIRING_GUID2)

        url = self._pairing_url(PAIRING_CODE2)
        data, _ = await utils.simple_get(url)

        await self.pairing.finish()

        # Verify content returned in pairingresponse
        parsed = parser.parse(data, tag_definitions.lookup_tag)
        self.assertEqual(parser.first(parsed, 'cmpa', 'cmpg'),
                         int(PAIRING_GUID2, 16))

        self.assertEqual(self.service.credentials, PAIRING_GUID2)

    async def test_failed_pairing(self):
        await self._start()

        url = self._pairing_url('wrong')
        _, status = await utils.simple_get(url)

        self.assertEqual(status, 500)

    def _pairing_url(self, pairing_code):
        service = self.zeroconf.registered_services[0]
        server = 'http://127.0.0.1:{}'.format(service.port)
        return '{}/pairing?pairingcode={}&servicename=test'.format(
            server, pairing_code)
