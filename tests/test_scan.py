"""Functional tests using the API with a fake Apple TV."""

import pyatv
import ipaddress
import asynctest

from pyatv.conf import AppleTV
from tests import zeroconf_stub


HOMESHARING_SERVICE_1 = zeroconf_stub.homesharing_service(
    'AAAA', b'Apple TV 1', '10.0.0.1', b'aaaa')
HOMESHARING_SERVICE_2 = zeroconf_stub.homesharing_service(
    'BBBB', b'Apple TV 2', '10.0.0.2', b'bbbb')
HOMESHARING_SERVICE_3 = zeroconf_stub.homesharing_service(
    'CCCC', b'Apple TV 3', '10.0.0.3', b'cccc')
DEVICE_SERVICE_1 = zeroconf_stub.device_service(
    'CCCC', b'Apple TV 3', '10.0.0.3')
MRP_SERVICE_1 = zeroconf_stub.mrp_service(
    'DDDD', b'Apple TV 4', '10.0.0.4')
MRP_SERVICE_2 = zeroconf_stub.mrp_service(
    'EEEE', b'Apple TV 5', '10.0.0.5')
AIRPLAY_SERVICE_1 = zeroconf_stub.airplay_service(
    'Apple TV 6', '10.0.0.6')


class FunctionalTest(asynctest.TestCase):

    async def test_scan_no_device_found(self):
        zeroconf_stub.stub(pyatv)

        atvs = await pyatv.scan_for_apple_tvs(self.loop, timeout=0)
        self.assertEqual(len(atvs), 0)

    async def test_scan_for_apple_tvs(self):
        zeroconf_stub.stub(
            pyatv, HOMESHARING_SERVICE_1, HOMESHARING_SERVICE_2,
            MRP_SERVICE_1, AIRPLAY_SERVICE_1)

        atvs = await pyatv.scan_for_apple_tvs(self.loop, timeout=0)
        self.assertEqual(len(atvs), 3)

        # First device
        dev1 = AppleTV(ipaddress.ip_address('10.0.0.1'), 'Apple TV 1')
        self.assertIn(dev1, atvs)

        # Second device
        dev2 = AppleTV(ipaddress.ip_address('10.0.0.2'), 'Apple TV 2')
        self.assertIn(dev2, atvs)

        # Third device
        dev3 = AppleTV(ipaddress.ip_address('10.0.0.4'), 'Apple TV 4')
        self.assertIn(dev3, atvs)

    async def test_scan_abort_on_first_found(self):
        zeroconf_stub.stub(pyatv, HOMESHARING_SERVICE_1, HOMESHARING_SERVICE_2)

        atvs = await pyatv.scan_for_apple_tvs(
            self.loop, timeout=0, abort_on_found=True)
        self.assertEqual(len(atvs), 1)
        self.assertEqual(atvs[0].name, 'Apple TV 1')

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

        dev1 = AppleTV(ipaddress.ip_address('10.0.0.4'), 'Apple TV 4')
        self.assertIn(dev1, atvs)

        dev2 = AppleTV(ipaddress.ip_address('10.0.0.5'), 'Apple TV 5')
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
            self.loop, timeout=0, only_usable=False, device_ip='10.0.0.2')
        self.assertEqual(len(atvs), 1)
        self.assertEqual(atvs[0].name, 'Apple TV 2')
        self.assertEqual(atvs[0].address, ipaddress.ip_address('10.0.0.2'))
