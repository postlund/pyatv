"""Functional tests using the API with a fake Apple TV."""

import pyatv
import ipaddress
import asynctest

from pyatv.conf import AppleTV
from tests import getmac_stub, zeroconf_stub


IP_1 = '10.0.0.1'
IP_2 = '10.0.0.2'
IP_3 = '10.0.0.3'
IP_4 = '10.0.0.4'
IP_5 = '10.0.0.5'
IP_6 = '10.0.0.6'

DEVICE_ID_1 = 'id1'
DEVICE_ID_2 = 'id2'
DEVICE_ID_3 = 'id3'
DEVICE_ID_4 = 'id4'
DEVICE_ID_5 = 'id5'
DEVICE_ID_6 = 'id6'

HOMESHARING_SERVICE_1 = zeroconf_stub.homesharing_service(
    'AAAA', b'Apple TV 1', IP_1, b'aaaa')
HOMESHARING_SERVICE_2 = zeroconf_stub.homesharing_service(
    'BBBB', b'Apple TV 2', IP_2, b'bbbb')
HOMESHARING_SERVICE_3 = zeroconf_stub.homesharing_service(
    'CCCC', b'Apple TV 3', IP_3, b'cccc')
DEVICE_SERVICE_1 = zeroconf_stub.device_service(
    'CCCC', b'Apple TV 3', IP_3)
MRP_SERVICE_1 = zeroconf_stub.mrp_service(
    'DDDD', b'Apple TV 4', IP_4)
MRP_SERVICE_2 = zeroconf_stub.mrp_service(
    'EEEE', b'Apple TV 5', IP_5)
AIRPLAY_SERVICE_1 = zeroconf_stub.airplay_service(
    'Apple TV 6', IP_6)
NO_DEVICE_ID_SERVICE = zeroconf_stub.airplay_service(
    'Apple TV', getmac_stub.IP_UNKNOWN)
EXCEPTION_DEVICE_ID_SERVICE = zeroconf_stub.airplay_service(
    'Apple TV', getmac_stub.IP_EXCEPTION)


class FunctionalTest(asynctest.TestCase):

    def setUp(self):
        mapping = {
          IP_1: DEVICE_ID_1,
          IP_2: DEVICE_ID_2,
          IP_3: DEVICE_ID_3,
          IP_4: DEVICE_ID_4,
          IP_5: DEVICE_ID_5,
          IP_6: DEVICE_ID_6,
        }
        getmac_stub.stub(pyatv, mapping=mapping)

    async def test_scan_no_device_found(self):
        zeroconf_stub.stub(pyatv)

        atvs = await pyatv.scan_for_apple_tvs(self.loop, timeout=0)
        self.assertEqual(len(atvs), 0)

    async def test_scan_device_id_missing(self):
        zeroconf_stub.stub(pyatv, NO_DEVICE_ID_SERVICE)

        atvs = await pyatv.scan_for_apple_tvs(
          self.loop, timeout=0, only_usable=False)
        self.assertEqual(len(atvs), 1)
        self.assertIsNone(atvs[0].device_id)

    # Defensive test for general failures (maybe not necessary)
    async def test_scan_device_id_failure(self):
        zeroconf_stub.stub(pyatv, EXCEPTION_DEVICE_ID_SERVICE)

        atvs = await pyatv.scan_for_apple_tvs(
          self.loop, timeout=0, only_usable=False)
        self.assertEqual(len(atvs), 1)
        self.assertIsNone(atvs[0].device_id)

    async def test_scan_for_apple_tvs(self):
        zeroconf_stub.stub(
            pyatv, HOMESHARING_SERVICE_1, HOMESHARING_SERVICE_2,
            MRP_SERVICE_1, AIRPLAY_SERVICE_1)

        atvs = await pyatv.scan_for_apple_tvs(self.loop, timeout=0)
        self.assertEqual(len(atvs), 3)

        # First device
        dev1 = AppleTV(ipaddress.ip_address(IP_1), DEVICE_ID_1, 'Apple TV 1')
        self.assertIn(dev1, atvs)

        # Second device
        dev2 = AppleTV(ipaddress.ip_address(IP_2), DEVICE_ID_2, 'Apple TV 2')
        self.assertIn(dev2, atvs)

        # Third device
        dev3 = AppleTV(ipaddress.ip_address(IP_4), DEVICE_ID_4, 'Apple TV 4')
        self.assertIn(dev3, atvs)

    async def test_scan_abort_on_first_usable_found(self):
        zeroconf_stub.stub(
            pyatv,
            HOMESHARING_SERVICE_1, HOMESHARING_SERVICE_2)

        atvs = await pyatv.scan_for_apple_tvs(
            self.loop, timeout=0, abort_on_found=True)
        self.assertEqual(len(atvs), 1)
        self.assertEqual(atvs[0].name, 'Apple TV 1')

    async def test_scan_abort_airplay_unusable(self):
        zeroconf_stub.stub(pyatv, AIRPLAY_SERVICE_1)

        atvs = await pyatv.scan_for_apple_tvs(
            self.loop, timeout=0, abort_on_found=True)
        self.assertEqual(len(atvs), 0)

    async def test_scan_all_devices(self):
        zeroconf_stub.stub(pyatv, DEVICE_SERVICE_1)

        atvs = await pyatv.scan_for_apple_tvs(
            self.loop, timeout=0, only_usable=False)
        self.assertEqual(len(atvs), 1)
        self.assertEqual(atvs[0].name, 'Apple TV 3')
        self.assertEqual(atvs[0].address, ipaddress.ip_address('10.0.0.3'))

        services = atvs[0].services()
        self.assertEqual(len(services), 1)

        service = services[0]
        self.assertEqual(service.port, 3689)

    async def test_scan_home_sharing_overrules(self):
        zeroconf_stub.stub(pyatv, DEVICE_SERVICE_1, HOMESHARING_SERVICE_3)

        atvs = await pyatv.scan_for_apple_tvs(self.loop, timeout=0)
        self.assertEqual(len(atvs), 1)
        self.assertEqual(atvs[0].name, 'Apple TV 3')
        self.assertEqual(atvs[0].address, ipaddress.ip_address('10.0.0.3'))

        service = atvs[0].usable_service()
        self.assertEqual(service.device_credentials, 'cccc')
        self.assertEqual(service.port, 3689)

    async def test_scan_mrp(self):
        zeroconf_stub.stub(pyatv, MRP_SERVICE_1, MRP_SERVICE_2)

        atvs = await pyatv.scan_for_apple_tvs(
            self.loop, only_usable=False, timeout=0)
        self.assertEqual(len(atvs), 2)

        dev1 = AppleTV(ipaddress.ip_address(IP_4), DEVICE_ID_4, 'Apple TV 4')
        self.assertIn(dev1, atvs)

        dev2 = AppleTV(ipaddress.ip_address(IP_5), DEVICE_ID_5, 'Apple TV 5')
        self.assertIn(dev2, atvs)

    async def test_scan_airplay_device(self):
        zeroconf_stub.stub(pyatv, AIRPLAY_SERVICE_1)

        atvs = await pyatv.scan_for_apple_tvs(
            self.loop, timeout=0, only_usable=False)
        self.assertEqual(len(atvs), 1)
        self.assertEqual(atvs[0].name, 'Apple TV 6')
        self.assertEqual(atvs[0].address, ipaddress.ip_address('10.0.0.6'))

        services = atvs[0].services()
        self.assertEqual(len(services), 1)

        service = services[0]
        self.assertEqual(service.port, 7000)

    async def test_scan_for_particular_device(self):
        zeroconf_stub.stub(pyatv, HOMESHARING_SERVICE_1, HOMESHARING_SERVICE_2)

        atvs = await pyatv.scan_for_apple_tvs(
            self.loop, timeout=0, only_usable=False, device_id=DEVICE_ID_2)
        self.assertEqual(len(atvs), 1)
        self.assertEqual(atvs[0].name, 'Apple TV 2')
        self.assertEqual(atvs[0].address, ipaddress.ip_address(IP_2))
