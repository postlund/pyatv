"""Functional tests using the API with a fake Apple TV."""

import pyatv
import ipaddress
import asynctest

from pyatv import AppleTVDevice
from tests import zeroconf_stub


HOMESHARING_SERVICE_1 = zeroconf_stub.homesharing_service(
    'AAAA', b'Apple TV 1', '10.0.0.1', b'aaaa')
HOMESHARING_SERVICE_2 = zeroconf_stub.homesharing_service(
    'BBBB', b'Apple TV 2', '10.0.0.2', b'bbbb')
HOMESHARING_SERVICE_3 = zeroconf_stub.homesharing_service(
    'CCCC', b'Apple TV 3', '10.0.0.3', b'cccc')
DEVICE_SERVICE_1 = zeroconf_stub.device_service(
    'CCCC', b'Apple TV 3', '10.0.0.3')


class FunctionalTest(asynctest.TestCase):

    def test_scan_no_device_found(self):
        zeroconf_stub.stub(pyatv)

        atvs = yield from pyatv.scan_for_apple_tvs(self.loop, timeout=0)
        self.assertEqual(len(atvs), 0)

    def test_scan_for_apple_tvs(self):
        zeroconf_stub.stub(pyatv, HOMESHARING_SERVICE_1, HOMESHARING_SERVICE_2)

        atvs = yield from pyatv.scan_for_apple_tvs(self.loop, timeout=0)
        self.assertEqual(len(atvs), 2)

        # First device
        dev1 = AppleTVDevice(
            'Apple TV 1', ipaddress.ip_address('10.0.0.1'), 'aaaa')
        self.assertIn(dev1, atvs)

        # Second device
        dev2 = AppleTVDevice(
            'Apple TV 2', ipaddress.ip_address('10.0.0.2'), 'bbbb')
        self.assertIn(dev2, atvs)

    def test_scan_abort_on_first_found(self):
        zeroconf_stub.stub(pyatv, HOMESHARING_SERVICE_1, HOMESHARING_SERVICE_2)

        atvs = yield from pyatv.scan_for_apple_tvs(
            self.loop, timeout=0, abort_on_found=True)
        self.assertEqual(len(atvs), 1)
        self.assertEqual(atvs[0].name, 'Apple TV 1')

    def test_scan_only_home_sharing(self):
        zeroconf_stub.stub(pyatv, DEVICE_SERVICE_1, HOMESHARING_SERVICE_1)

        atvs = yield from pyatv.scan_for_apple_tvs(self.loop, timeout=0)
        self.assertEqual(len(atvs), 1)
        self.assertEqual(atvs[0].name, 'Apple TV 1')
        self.assertEqual(atvs[0].address, ipaddress.ip_address('10.0.0.1'))
        self.assertEqual(atvs[0].login_id, 'aaaa')
        self.assertEqual(atvs[0].port, 3689)

    def test_scan_all_devices(self):
        zeroconf_stub.stub(pyatv, DEVICE_SERVICE_1)

        atvs = yield from pyatv.scan_for_apple_tvs(
            self.loop, timeout=0, only_home_sharing=False)
        self.assertEqual(len(atvs), 1)
        self.assertEqual(atvs[0].name, 'Apple TV 3')
        self.assertEqual(atvs[0].address, ipaddress.ip_address('10.0.0.3'))
        self.assertEqual(atvs[0].login_id, None)
        self.assertEqual(atvs[0].port, 3689)

    def test_scan_home_sharing_overrules(self):
        zeroconf_stub.stub(pyatv, DEVICE_SERVICE_1, HOMESHARING_SERVICE_3)

        atvs = yield from pyatv.scan_for_apple_tvs(self.loop, timeout=0)
        self.assertEqual(len(atvs), 1)
        self.assertEqual(atvs[0].name, 'Apple TV 3')
        self.assertEqual(atvs[0].address, ipaddress.ip_address('10.0.0.3'))
        self.assertEqual(atvs[0].login_id, 'cccc')
        self.assertEqual(atvs[0].port, 3689)
