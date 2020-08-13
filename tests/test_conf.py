"""Unit tests for pyatv.conf."""

import pytest

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

DMAP_SERVICE = conf.DmapService(IDENTIFIER_1, None, port=PORT_1)
MRP_SERVICE = conf.MrpService(IDENTIFIER_2, PORT_2, properties=MRP_PROPERTIES)
AIRPLAY_SERVICE = conf.AirPlayService(
    IDENTIFIER_3, PORT_1, properties=AIRPLAY_PROPERTIES
)


@pytest.fixture
def config():
    yield conf.AppleTV(ADDRESS_1, NAME, deep_sleep=True, model=DeviceModel.Gen2)


def test_address_and_name(config):
    assert config.address == ADDRESS_1
    assert config.name == NAME


def test_equality(config):
    assert config == config

    atv2 = conf.AppleTV(ADDRESS_1, NAME)
    atv2.add_service(conf.AirPlayService(IDENTIFIER_1, PORT_1))
    assert config != atv2


def test_add_services_and_get(config):
    config.add_service(DMAP_SERVICE)
    config.add_service(MRP_SERVICE)
    config.add_service(AIRPLAY_SERVICE)

    services = config.services
    assert len(services), 3

    assert DMAP_SERVICE in services
    assert MRP_SERVICE in services
    assert AIRPLAY_SERVICE in services

    assert config.get_service(Protocol.DMAP) == DMAP_SERVICE
    assert config.get_service(Protocol.MRP) == MRP_SERVICE
    assert config.get_service(Protocol.AirPlay) == AIRPLAY_SERVICE


def test_identifier_order(config):
    assert config.identifier is None

    config.add_service(DMAP_SERVICE)
    assert config.identifier == IDENTIFIER_1

    config.add_service(MRP_SERVICE)
    assert config.identifier == IDENTIFIER_2

    config.add_service(AIRPLAY_SERVICE)
    assert config.identifier == IDENTIFIER_2


def test_add_airplay_service(config):
    config.add_service(AIRPLAY_SERVICE)

    airplay = config.get_service(Protocol.AirPlay)
    assert airplay.protocol == Protocol.AirPlay
    assert airplay.port == PORT_1


def test_main_service_no_service(config):
    with pytest.raises(exceptions.NoServiceError):
        config.main_service()


def test_main_service_airplay_no_service(config):
    config.add_service(AIRPLAY_SERVICE)
    with pytest.raises(exceptions.NoServiceError):
        config.main_service()


def test_main_service_get_service(config):
    config.add_service(DMAP_SERVICE)
    assert config.main_service() == DMAP_SERVICE

    config.add_service(MRP_SERVICE)
    assert config.main_service() == MRP_SERVICE


def test_main_service_override_protocol(config):
    config.add_service(DMAP_SERVICE)
    config.add_service(MRP_SERVICE)
    assert config.main_service(protocol=DMAP_SERVICE.protocol) == DMAP_SERVICE


def test_set_credentials_for_missing_service(config):
    assert not config.set_credentials(Protocol.DMAP, "dummy")


def test_set_credentials(config):
    config.add_service(DMAP_SERVICE)
    assert config.get_service(Protocol.DMAP).credentials is None

    config.set_credentials(Protocol.DMAP, "dummy")
    assert config.get_service(Protocol.DMAP).credentials == "dummy"


def test_empty_device_info(config):
    config = conf.AppleTV(ADDRESS_1, NAME)
    device_info = config.device_info
    assert device_info.operating_system == OperatingSystem.Unknown
    assert device_info.version is None
    assert device_info.build_number is None
    assert device_info.model == DeviceModel.Unknown
    assert device_info.mac is None


def test_tvos_device_info(config):
    config.add_service(MRP_SERVICE)
    config.add_service(AIRPLAY_SERVICE)

    device_info = config.device_info
    assert device_info.operating_system == OperatingSystem.TvOS
    assert device_info.version == "8.0.0"
    assert device_info.build_number == "17K795"
    assert device_info.model == DeviceModel.Gen4K
    assert device_info.mac == "FF:EE:DD:CC:BB:AA"


def test_tvos_device_info_no_airplay(config):
    config.add_service(MRP_SERVICE)

    device_info = config.device_info
    assert device_info.operating_system == OperatingSystem.TvOS
    assert device_info.version == "13.3.1"
    assert device_info.build_number == "17K795"
    assert device_info.model == DeviceModel.Gen2
    assert device_info.mac == "FF:EE:DD:CC:BB:AA"


def test_legacy_device_info(config):
    config.add_service(DMAP_SERVICE)
    config.add_service(AIRPLAY_SERVICE)

    device_info = config.device_info
    assert device_info.operating_system == OperatingSystem.Legacy
    assert device_info.version == "8.0.0"
    assert device_info.build_number is None
    assert device_info.model == DeviceModel.Gen4K
    assert device_info.mac == "AA:BB:CC:DD:EE:FF"


def test_ready_dmap(config):
    assert not config.ready

    config.add_service(AIRPLAY_SERVICE)
    assert not config.ready

    config.add_service(DMAP_SERVICE)
    assert config.ready


def test_ready_mrp(config):
    assert not config.ready

    config.add_service(AIRPLAY_SERVICE)
    assert not config.ready

    config.add_service(MRP_SERVICE)
    assert config.ready


# Name collisions on the network results in _X being added to the identifier,
# which should be stripped
def test_dmap_identifier_strip():
    service = conf.DmapService("abcd_2", "dummy")
    assert service.identifier == "abcd"


# This test is a bit strange and couples to protocol specific services,
# but it's mainly to exercise string as that is important. Might refactor
# this in the future.
def test_to_str(config):
    config.add_service(conf.DmapService(IDENTIFIER_1, "LOGIN_ID"))
    config.add_service(conf.MrpService(IDENTIFIER_2, PORT_2))

    # Check for some keywords to not lock up format too much
    output = str(config)
    assert ADDRESS_1 in output
    assert NAME in output
    assert "LOGIN_ID" in output
    assert str(PORT_2) in output
    assert "3689" in output
    assert "Deep Sleep: True" in output
