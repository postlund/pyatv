"""Functional tests using the API with a fake Apple TV."""

import pyatv
import ipaddress
import asynctest

from unittest.mock import patch

from pyatv.const import Protocol
from tests import fake_udns, zeroconf_stub


IP_1 = '10.0.0.1'
IP_2 = '10.0.0.2'
IP_3 = '10.0.0.3'
IP_4 = '10.0.0.4'
IP_5 = '10.0.0.5'
IP_6 = '10.0.0.6'
IP_LOCALHOST = '127.0.0.1'

HSGID = 'hsgid'

MRP_ID_1 = 'mrp_id_1'
MRP_ID_2 = 'mrp_id_2'

AIRPLAY_ID = 'AA:BB:CC:DD:EE:FF'

HOMESHARING_SERVICE_1 = zeroconf_stub.homesharing_service(
    'AAAA', b'Apple TV 1', IP_1, b'aaaa')
HOMESHARING_SERVICE_2 = zeroconf_stub.homesharing_service(
    'BBBB', b'Apple TV 2', IP_2, b'bbbb')
HOMESHARING_SERVICE_3 = zeroconf_stub.homesharing_service(
    'CCCC', b'Apple TV 3', IP_3, b'cccc')
DEVICE_SERVICE_1 = zeroconf_stub.device_service(
    'CCCC', b'Apple TV 3', IP_3)
MRP_SERVICE_1 = zeroconf_stub.mrp_service(
    'DDDD', b'Apple TV 4', IP_4, MRP_ID_1)
MRP_SERVICE_2 = zeroconf_stub.mrp_service(
    'EEEE', b'Apple TV 5', IP_5, MRP_ID_2)
AIRPLAY_SERVICE_1 = zeroconf_stub.airplay_service(
    'Apple TV 6', IP_6, AIRPLAY_ID)


def _get_atv(atvs, ip):
    for atv in atvs:
        if atv.address == ipaddress.ip_address(ip):
            return atv
    return None


class ScanZeroconfTest(asynctest.TestCase):

    async def test_scan_no_device_found(self):
        zeroconf_stub.stub(pyatv)

        atvs = await pyatv.scan(self.loop, timeout=0)
        self.assertEqual(len(atvs), 0)

    async def test_scan(self):
        zeroconf_stub.stub(
            pyatv, HOMESHARING_SERVICE_1, HOMESHARING_SERVICE_2,
            MRP_SERVICE_1, AIRPLAY_SERVICE_1)

        atvs = await pyatv.scan(self.loop, timeout=0)
        self.assertEqual(len(atvs), 4)

        # First device
        dev1 = _get_atv(atvs, IP_1)
        self.assertIsNotNone(dev1)
        self.assertEqual(dev1.identifier, 'AAAA')

        # Second device
        dev2 = _get_atv(atvs, IP_2)
        self.assertIsNotNone(dev2)
        self.assertEqual(dev2.identifier, 'BBBB')

        # Third device
        dev3 = _get_atv(atvs, IP_4)
        self.assertIsNotNone(dev3)
        self.assertEqual(dev3.identifier, MRP_ID_1)

        # Fourth device
        dev4 = _get_atv(atvs, IP_6)
        self.assertIsNotNone(dev4)
        self.assertEqual(dev4.identifier, AIRPLAY_ID)

    async def test_scan_no_home_sharing(self):
        zeroconf_stub.stub(pyatv, DEVICE_SERVICE_1)

        atvs = await pyatv.scan(self.loop, timeout=0)
        self.assertEqual(len(atvs), 1)
        self.assertEqual(atvs[0].name, 'Apple TV 3')
        self.assertEqual(atvs[0].address, ipaddress.ip_address(IP_3))

        atv = atvs[0]
        self.assertEqual(
            atv.get_service(Protocol.DMAP).port, 3689)

    async def test_scan_home_sharing_merge(self):
        zeroconf_stub.stub(pyatv, DEVICE_SERVICE_1, HOMESHARING_SERVICE_3)

        atvs = await pyatv.scan(self.loop, timeout=0)
        self.assertEqual(len(atvs), 1)
        self.assertEqual(atvs[0].name, 'Apple TV 3')
        self.assertEqual(atvs[0].address, ipaddress.ip_address('10.0.0.3'))

        service = atvs[0].main_service()
        self.assertEqual(service.credentials, 'cccc')
        self.assertEqual(service.port, 3689)

    async def test_scan_mrp(self):
        zeroconf_stub.stub(
          pyatv, MRP_SERVICE_1, MRP_SERVICE_2, DEVICE_SERVICE_1)

        atvs = await pyatv.scan(
          self.loop, timeout=0, protocol=Protocol.MRP)
        self.assertEqual(len(atvs), 2)

        dev1 = _get_atv(atvs, IP_4)
        self.assertIsNotNone(dev1)
        self.assertEqual(dev1.name, 'Apple TV 4')
        self.assertIsNotNone(dev1.get_service(Protocol.MRP))

        dev2 = _get_atv(atvs, IP_5)
        self.assertIsNotNone(dev2)
        self.assertEqual(dev2.name, 'Apple TV 5')
        self.assertIsNotNone(dev2.get_service(Protocol.MRP))

    async def test_scan_airplay_device(self):
        zeroconf_stub.stub(pyatv, AIRPLAY_SERVICE_1)

        atvs = await pyatv.scan(self.loop, timeout=0)
        self.assertEqual(len(atvs), 1)
        self.assertEqual(atvs[0].name, 'Apple TV 6')
        self.assertEqual(atvs[0].address, ipaddress.ip_address('10.0.0.6'))

        services = atvs[0].services
        self.assertEqual(len(services), 1)

        service = services[0]
        self.assertEqual(service.port, 7000)

    async def test_scan_for_particular_device(self):
        zeroconf_stub.stub(pyatv, HOMESHARING_SERVICE_1, HOMESHARING_SERVICE_2)

        atvs = await pyatv.scan(
            self.loop, timeout=0, identifier='BBBB')
        self.assertEqual(len(atvs), 1)
        self.assertEqual(atvs[0].name, 'Apple TV 2')
        self.assertEqual(atvs[0].address, ipaddress.ip_address(IP_2))


class ScanUnicastDnsTest(asynctest.TestCase):

    async def setUp(self, *services):
        self.server = fake_udns.FakeUdns(self.loop)
        await self.server.start()

    async def scan(self):
        port = str(self.server.port)
        with patch.dict('os.environ', {'PYATV_UDNS_PORT': port}):
            return await pyatv.scan(self.loop, hosts=[IP_LOCALHOST])

    def assertDevice(self, atv, name, address,
                     identifier, protocol, port, creds=None):
        self.assertEqual(atv.name, name)
        self.assertEqual(atv.address, address)
        self.assertEqual(atv.identifier, identifier)
        self.assertIsNotNone(atv.get_service(protocol))
        self.assertEqual(atv.get_service(protocol).port, port)
        self.assertEqual(atv.get_service(protocol).credentials, creds)

    async def test_scan_no_results(self):
        atvs = await self.scan()
        self.assertEqual(len(atvs), 0)

    async def test_missing_port(self):
        self.server.add_service(
            fake_udns.mrp_service('dummy', 'dummy', 'dummy', port=None))

        atvs = await self.scan()
        self.assertEqual(len(atvs), 0)

    async def test_missing_properties(self):
        self.server.add_service(
            fake_udns.FakeDnsService('dummy', 1234, None))

        atvs = await self.scan()
        self.assertEqual(len(atvs), 0)

    async def test_scan_mrp(self):
        self.server.add_service(
            fake_udns.mrp_service('Apple TV', 'Apple TV MRP', MRP_ID_1))

        atvs = await self.scan()
        self.assertEqual(len(atvs), 1)

        self.assertDevice(
            atvs[0], 'Apple TV MRP', IP_LOCALHOST,
            MRP_ID_1, Protocol.MRP, 49152)

    async def test_scan_airplay(self):
        self.server.add_service(
            fake_udns.airplay_service('Apple TV', AIRPLAY_ID))

        atvs = await self.scan()
        self.assertEqual(len(atvs), 1)

        self.assertDevice(
            atvs[0], 'Apple TV', IP_LOCALHOST,
            AIRPLAY_ID, Protocol.AirPlay, 7000)

    async def test_scan_homesharing(self):
        self.server.add_service(
            fake_udns.homesharing_service('abcd', 'Apple TV HS', HSGID))

        atvs = await self.scan()
        self.assertEqual(len(atvs), 1)

        self.assertDevice(
            atvs[0], 'Apple TV HS', IP_LOCALHOST,
            'abcd', Protocol.DMAP, 3689, HSGID)

    async def test_scan_no_homesharing(self):
        self.server.add_service(
            fake_udns.device_service('Apple TV', 'Apple TV Device'))

        atvs = await self.scan()
        self.assertEqual(len(atvs), 1)

        self.assertDevice(
            atvs[0], 'Apple TV Device', IP_LOCALHOST,
            'Apple TV', Protocol.DMAP, 3689)
