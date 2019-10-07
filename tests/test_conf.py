"""Unit tests for pyatv.conf."""

import unittest
from unittest.mock import MagicMock

from pyatv import (conf, const)

PROTOCOL_1 = 1
PROTOCOL_2 = 2
SUPPORTED_PROTOCOLS = [PROTOCOL_1, PROTOCOL_2]

ADDRESS_1 = '127.0.0.1'
ADDRESS_2 = '192.168.0.1'
NAME = 'Alice'
PORT_1 = 1234
PORT_2 = 5678
DEVICE_ID_1 = 'id1'
DEVICE_ID_2 = 'id2'


class ConfTest(unittest.TestCase):

    def setUp(self):
        self.atv = conf.AppleTV(
            ADDRESS_1, DEVICE_ID_1,
            NAME, supported_services=SUPPORTED_PROTOCOLS)
        self.service_mock = MagicMock()
        self.service_mock.protocol = PROTOCOL_1
        self.service_mock.port = PORT_1
        self.service_mock.is_usable.return_value = False
        self.service_mock.superseeded_by.return_value = False

        self.service_mock2 = MagicMock()
        self.service_mock2.protocol = PROTOCOL_2
        self.service_mock2.port = PORT_2
        self.service_mock2.is_usable.return_value = False
        self.service_mock2.superseeded_by.return_value = False

    def test_address_and_name(self):
        self.assertEqual(self.atv.address, ADDRESS_1)
        self.assertEqual(self.atv.name, NAME)

    def test_equality(self):
        self.assertEqual(self.atv, self.atv)

        atv2 = conf.AppleTV(ADDRESS_1, DEVICE_ID_2, NAME)
        self.assertNotEqual(self.atv, atv2)

    def test_add_services_and_get(self):
        self.atv.add_service(self.service_mock)
        self.atv.add_service(self.service_mock2)

        services = self.atv.services()
        self.assertEqual(len(services), 2)

        self.assertIn(self.service_mock, services)
        self.assertIn(self.service_mock2, services)

        self.assertEqual(self.atv.get_service(PROTOCOL_1), self.service_mock)
        self.assertEqual(self.atv.get_service(PROTOCOL_2), self.service_mock2)

    def test_usable_service(self):
        self.assertIsNone(self.atv.usable_service())

        self.atv.add_service(self.service_mock)
        self.atv.add_service(self.service_mock2)
        self.assertIsNone(self.atv.usable_service())

        self.service_mock2.is_usable.return_value = True
        self.assertEqual(self.atv.usable_service(), self.service_mock2)

    def test_any_service_usable(self):
        self.assertFalse(self.atv.is_usable())

        self.atv.add_service(self.service_mock)
        self.assertFalse(self.atv.is_usable())

        self.service_mock.is_usable.return_value = True
        self.assertTrue(self.atv.is_usable())

    def test_default_airplay_service(self):
        airplay = self.atv.airplay_service()
        self.assertEqual(airplay.protocol, const.PROTOCOL_AIRPLAY)
        self.assertEqual(airplay.port, 7000)

    def test_add_airplay_service(self):
        airplay_mock = MagicMock()
        airplay_mock.port = PORT_1
        airplay_mock.protocol = const.PROTOCOL_AIRPLAY
        self.atv.add_service(airplay_mock)

        airplay = self.atv.airplay_service()
        self.assertEqual(airplay.protocol, const.PROTOCOL_AIRPLAY)
        self.assertEqual(airplay.port, PORT_1)

    def test_superseeded_by(self):
        self.atv.add_service(self.service_mock)

        mock = MagicMock()
        mock.protocol = PROTOCOL_1
        mock.port = PORT_1
        self.atv.add_service(mock)
        self.assertEqual(self.atv.get_service(PROTOCOL_1), self.service_mock)

        self.service_mock.superseeded_by.return_value = True
        self.atv.add_service(mock)
        self.assertEqual(self.atv.get_service(PROTOCOL_1), mock)

    # This test is a bit strange and couples to protocol specific services,
    # but it's mainly to exercise string as that is important. Might refactor
    # this in the future.
    def test_to_str(self):
        self.atv.add_service(conf.DmapService('LOGIN_ID'))
        self.atv.add_service(conf.MrpService(PORT_2))

        # Check for some keywords to not lock up format too much
        output = str(self.atv)
        self.assertIn(ADDRESS_1, output)
        self.assertIn(NAME, output)
        self.assertIn('LOGIN_ID', output)
        self.assertIn(str(PORT_2), output)
        self.assertIn('3689', output)
