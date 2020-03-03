"""Unit tests for pyatv.conf."""

import unittest

from pyatv import conf, exceptions
from pyatv.const import Protocol, OperatingSystem, DeviceModel

ADDRESS_1 = "127.0.0.1"
ADDRESS_2 = "192.168.0.1"
NAME = "Alice"
PORT_1 = 1234
PORT_2 = 5678
IDENTIFIER_1 = "id1"
IDENTIFIER_2 = "id2"
IDENTIFIER_3 = "id3"
CREDENTIALS_1 = "cred1"

MRP_PROPERTIES = {
    "SystemBuildVersion": "17K795",
    "macAddress": "ff:ee:dd:cc:bb:aa",
}

AIRPLAY_PROPERTIES = {
    "model": "AppleTV6,2",
    "deviceid": "aa:bb:cc:dd:ee:ff",
    "osvers": "8.0.0",
}


class ConfTest(unittest.TestCase):
    def setUp(self):
        self.config = conf.AppleTV(ADDRESS_1, NAME)
        self.dmap_service = conf.DmapService(IDENTIFIER_1, None, port=PORT_1)
        self.mrp_service = conf.MrpService(
            IDENTIFIER_2, PORT_2, properties=MRP_PROPERTIES
        )
        self.airplay_service = conf.AirPlayService(
            IDENTIFIER_3, PORT_1, properties=AIRPLAY_PROPERTIES
        )

    def test_address_and_name(self):
        self.assertEqual(self.config.address, ADDRESS_1)
        self.assertEqual(self.config.name, NAME)

    def test_equality(self):
        self.assertEqual(self.config, self.config)

        atv2 = conf.AppleTV(ADDRESS_1, NAME)
        atv2.add_service(conf.AirPlayService(IDENTIFIER_1, PORT_1))
        self.assertNotEqual(self.config, atv2)

    def test_add_services_and_get(self):
        self.config.add_service(self.dmap_service)
        self.config.add_service(self.mrp_service)
        self.config.add_service(self.airplay_service)

        services = self.config.services
        self.assertEqual(len(services), 3)

        self.assertIn(self.dmap_service, services)
        self.assertIn(self.mrp_service, services)
        self.assertIn(self.airplay_service, services)

        self.assertEqual(self.config.get_service(Protocol.DMAP), self.dmap_service)
        self.assertEqual(self.config.get_service(Protocol.MRP), self.mrp_service)
        self.assertEqual(
            self.config.get_service(Protocol.AirPlay), self.airplay_service
        )

    def test_identifier_order(self):
        self.assertIsNone(self.config.identifier)

        self.config.add_service(self.dmap_service)
        self.assertEqual(self.config.identifier, IDENTIFIER_1)

        self.config.add_service(self.mrp_service)
        self.assertEqual(self.config.identifier, IDENTIFIER_2)

        self.config.add_service(self.airplay_service)
        self.assertEqual(self.config.identifier, IDENTIFIER_2)

    def test_add_airplay_service(self):
        self.config.add_service(self.airplay_service)

        airplay = self.config.get_service(Protocol.AirPlay)
        self.assertEqual(airplay.protocol, Protocol.AirPlay)
        self.assertEqual(airplay.port, PORT_1)

    def test_main_service_no_service(self):
        with self.assertRaises(exceptions.NoServiceError):
            self.config.main_service()

    def test_main_service_airplay_no_service(self):
        self.config.add_service(self.airplay_service)
        with self.assertRaises(exceptions.NoServiceError):
            self.config.main_service()

    def test_main_service_get_service(self):
        self.config.add_service(self.dmap_service)
        self.assertEqual(self.config.main_service(), self.dmap_service)

        self.config.add_service(self.mrp_service)
        self.assertEqual(self.config.main_service(), self.mrp_service)

    def test_main_service_override_protocol(self):
        self.config.add_service(self.dmap_service)
        self.config.add_service(self.mrp_service)
        self.assertEqual(
            self.config.main_service(protocol=self.dmap_service.protocol),
            self.dmap_service,
        )

    def test_set_credentials_for_missing_service(self):
        self.assertFalse(self.config.set_credentials(Protocol.DMAP, "dummy"))

    def test_set_credentials(self):
        self.config.add_service(self.dmap_service)
        self.assertIsNone(self.config.get_service(Protocol.DMAP).credentials)

        self.config.set_credentials(Protocol.DMAP, "dummy")
        self.assertEqual(self.config.get_service(Protocol.DMAP).credentials, "dummy")

    def test_empty_device_info(self):
        device_info = self.config.device_info
        self.assertEqual(device_info.operating_system, OperatingSystem.Unknown)
        self.assertIsNone(device_info.version)
        self.assertIsNone(device_info.build_number)
        self.assertEqual(device_info.model, DeviceModel.Unknown)
        self.assertIsNone(device_info.mac)

    def test_tvos_device_info(self):
        self.config.add_service(self.mrp_service)
        self.config.add_service(self.airplay_service)

        device_info = self.config.device_info
        self.assertEqual(device_info.operating_system, OperatingSystem.TvOS)
        self.assertEqual(device_info.version, "8.0.0")
        self.assertEqual(device_info.build_number, "17K795")
        self.assertEqual(device_info.model, DeviceModel.Gen4K)
        self.assertEqual(device_info.mac, "FF:EE:DD:CC:BB:AA")

    def test_tvos_device_info_no_airplay(self):
        self.config.add_service(self.mrp_service)

        device_info = self.config.device_info
        self.assertEqual(device_info.operating_system, OperatingSystem.TvOS)
        self.assertEqual(device_info.version, "13.3.1")
        self.assertEqual(device_info.build_number, "17K795")
        self.assertEqual(device_info.model, DeviceModel.Unknown)
        self.assertEqual(device_info.mac, "FF:EE:DD:CC:BB:AA")

    def test_legacy_device_info(self):
        self.config.add_service(self.dmap_service)
        self.config.add_service(self.airplay_service)

        device_info = self.config.device_info
        self.assertEqual(device_info.operating_system, OperatingSystem.Legacy)
        self.assertEqual(device_info.version, "8.0.0")
        self.assertIsNone(device_info.build_number)
        self.assertEqual(device_info.model, DeviceModel.Gen4K)
        self.assertEqual(device_info.mac, "AA:BB:CC:DD:EE:FF")

    def test_ready_dmap(self):
        self.assertFalse(self.config.ready)

        self.config.add_service(self.airplay_service)
        self.assertFalse(self.config.ready)

        self.config.add_service(self.dmap_service)
        self.assertTrue(self.config.ready)

    def test_ready_mrp(self):
        self.assertFalse(self.config.ready)

        self.config.add_service(self.airplay_service)
        self.assertFalse(self.config.ready)

        self.config.add_service(self.mrp_service)
        self.assertTrue(self.config.ready)

    # This test is a bit strange and couples to protocol specific services,
    # but it's mainly to exercise string as that is important. Might refactor
    # this in the future.
    def test_to_str(self):
        self.config.add_service(conf.DmapService(IDENTIFIER_1, "LOGIN_ID"))
        self.config.add_service(conf.MrpService(IDENTIFIER_2, PORT_2))

        # Check for some keywords to not lock up format too much
        output = str(self.config)
        self.assertIn(ADDRESS_1, output)
        self.assertIn(NAME, output)
        self.assertIn("LOGIN_ID", output)
        self.assertIn(str(PORT_2), output)
        self.assertIn("3689", output)
