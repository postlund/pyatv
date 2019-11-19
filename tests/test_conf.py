"""Unit tests for pyatv.conf."""

import unittest
from unittest.mock import MagicMock

from pyatv import (conf, const, exceptions)
from pyatv.const import (
  PROTOCOL_AIRPLAY, PROTOCOL_DMAP, PROTOCOL_MRP)

ADDRESS_1 = '127.0.0.1'
ADDRESS_2 = '192.168.0.1'
NAME = 'Alice'
PORT_1 = 1234
PORT_2 = 5678
IDENTIFIER_1 = 'id1'
IDENTIFIER_2 = 'id2'
CREDENTIALS_1 = 'cred1'


class ConfTest(unittest.TestCase):

    def setUp(self):
        self.config = conf.AppleTV(ADDRESS_1, NAME)
        self.service_mock = MagicMock()
        self.service_mock.protocol = const.PROTOCOL_DMAP
        self.service_mock.port = PORT_1
        self.service_mock.identifier = IDENTIFIER_1
        self.service_mock.credentials = None

        self.service_mock2 = MagicMock()
        self.service_mock2.protocol = const.PROTOCOL_MRP
        self.service_mock2.port = PORT_2
        self.service_mock2.identifier = IDENTIFIER_2

        self.airplay_mock = MagicMock()
        self.airplay_mock.port = PORT_1
        self.airplay_mock.protocol = const.PROTOCOL_AIRPLAY

    def test_address_and_name(self):
        self.assertEqual(self.config.address, ADDRESS_1)
        self.assertEqual(self.config.name, NAME)

    def test_equality(self):
        self.assertEqual(self.config, self.config)

        atv2 = conf.AppleTV(ADDRESS_1, NAME)
        atv2.add_service(conf.AirPlayService(IDENTIFIER_1, PORT_1))
        self.assertNotEqual(self.config, atv2)

    def test_add_services_and_get(self):
        self.config.add_service(self.service_mock)
        self.config.add_service(self.service_mock2)

        services = self.config.services
        self.assertEqual(len(services), 3)

        self.assertIn(self.service_mock, services)
        self.assertIn(self.service_mock2, services)

        self.assertEqual(
            self.config.get_service(PROTOCOL_DMAP), self.service_mock)
        self.assertEqual(
            self.config.get_service(PROTOCOL_MRP), self.service_mock2)
        self.assertIsNotNone(self.config.get_service(PROTOCOL_AIRPLAY))

    def test_identifier(self):
        self.assertIsNone(self.config.identifier)

        self.config.add_service(self.service_mock)
        self.assertEqual(self.config.identifier, IDENTIFIER_1)

        self.config.add_service(self.service_mock2)
        self.assertEqual(self.config.identifier, IDENTIFIER_1)

        services = self.config.services
        self.assertEqual(len(services), 3)
        self.assertIn(self.service_mock, services)
        self.assertIn(self.service_mock2, services)

    def test_default_airplay_service(self):
        airplay = self.config.get_service(const.PROTOCOL_AIRPLAY)
        self.assertEqual(airplay.protocol, const.PROTOCOL_AIRPLAY)
        self.assertEqual(airplay.port, 7000)

    def test_add_airplay_service(self):
        self.config.add_service(self.airplay_mock)

        airplay = self.config.get_service(PROTOCOL_AIRPLAY)
        self.assertEqual(airplay.protocol, const.PROTOCOL_AIRPLAY)
        self.assertEqual(airplay.port, PORT_1)

    def test_main_service_no_service(self):
        with self.assertRaises(exceptions.NoServiceError):
            self.config.main_service()

    def test_main_service_airplay_no_service(self):
        self.config.add_service(self.airplay_mock)
        with self.assertRaises(exceptions.NoServiceError):
            self.config.main_service()

    def test_main_service_get_service(self):
        self.config.add_service(self.service_mock)
        self.assertEqual(self.config.main_service(), self.service_mock)

        self.config.add_service(self.service_mock2)
        self.assertEqual(self.config.main_service(), self.service_mock2)

    def test_main_service_override_protocol(self):
        self.config.add_service(self.service_mock)
        self.config.add_service(self.service_mock2)
        self.assertEqual(
            self.config.main_service(protocol=self.service_mock.protocol),
            self.service_mock)

    def test_set_credentials_for_missing_service(self):
        self.assertFalse(self.config.set_credentials(PROTOCOL_DMAP, 'dummy'))

    def test_set_credentials(self):
        self.config.add_service(self.service_mock)
        self.assertIsNone(self.config.get_service(PROTOCOL_DMAP).credentials)

        self.config.set_credentials(PROTOCOL_DMAP, 'dummy')
        self.assertEqual(
            self.config.get_service(PROTOCOL_DMAP).credentials, 'dummy')

    # This test is a bit strange and couples to protocol specific services,
    # but it's mainly to exercise string as that is important. Might refactor
    # this in the future.
    def test_to_str(self):
        self.config.add_service(conf.DmapService(IDENTIFIER_1, 'LOGIN_ID'))
        self.config.add_service(conf.MrpService(IDENTIFIER_2, PORT_2))

        # Check for some keywords to not lock up format too much
        output = str(self.config)
        self.assertIn(ADDRESS_1, output)
        self.assertIn(NAME, output)
        self.assertIn('LOGIN_ID', output)
        self.assertIn(str(PORT_2), output)
        self.assertIn('3689', output)
