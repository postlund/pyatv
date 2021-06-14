"""Unit tests for pyatv.conf."""

import pytest

from pyatv import conf, exceptions
from pyatv.const import DeviceModel, OperatingSystem, Protocol

ADDRESS_1 = "127.0.0.1"
ADDRESS_2 = "192.168.0.1"
NAME = "Alice"
PORT_1 = 1234
PORT_2 = 5678
PORT_3 = 1111
PORT_4 = 5555
IDENTIFIER_1 = "id1"
IDENTIFIER_2 = "id2"
IDENTIFIER_3 = "id3"
IDENTIFIER_4 = "id4"
CREDENTIALS_1 = "cred1"

MRP_PROPERTIES = {
    "systembuildversion": "17K795",
    "macaddress": "ff:ee:dd:cc:bb:aa",
}

AIRPLAY_PROPERTIES = {
    "model": "AppleTV6,2",
    "deviceid": "ff:ee:dd:cc:bb:aa",
    "osvers": "8.0.0",
}

RAOP_PROPERTIES = {
    "am": "AudioAccessory5,1",
    "ov": "14.5",
}

AIRPORT_PROPERTIES = {
    "am": "AirPort10,115",
}

DMAP_SERVICE = conf.DmapService(IDENTIFIER_1, None, port=PORT_1)
MRP_SERVICE = conf.MrpService(IDENTIFIER_2, PORT_2, properties=MRP_PROPERTIES)
AIRPLAY_SERVICE = conf.AirPlayService(
    IDENTIFIER_3, PORT_1, properties=AIRPLAY_PROPERTIES
)
COMPANION_SERVICE = conf.CompanionService(PORT_3)
RAOP_SERVICE = conf.RaopService(IDENTIFIER_4, PORT_4, properties=RAOP_PROPERTIES)
AIRPORT_SERVICE = conf.RaopService(IDENTIFIER_1, PORT_1, properties=AIRPORT_PROPERTIES)


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
    config.add_service(COMPANION_SERVICE)
    config.add_service(RAOP_SERVICE)

    services = config.services
    assert len(services), 4

    assert DMAP_SERVICE in services
    assert MRP_SERVICE in services
    assert AIRPLAY_SERVICE in services
    assert COMPANION_SERVICE in services

    assert config.get_service(Protocol.DMAP) == DMAP_SERVICE
    assert config.get_service(Protocol.MRP) == MRP_SERVICE
    assert config.get_service(Protocol.AirPlay) == AIRPLAY_SERVICE
    assert config.get_service(Protocol.RAOP) == RAOP_SERVICE


def test_identifier_order(config):
    assert config.identifier is None

    config.add_service(RAOP_SERVICE)
    assert config.identifier == IDENTIFIER_4

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


def test_main_service_companion_no_service(config):
    config.add_service(COMPANION_SERVICE)
    with pytest.raises(exceptions.NoServiceError):
        config.main_service()


def test_main_service_get_service(config):
    config.add_service(RAOP_SERVICE)
    assert config.main_service() == RAOP_SERVICE

    config.add_service(AIRPLAY_SERVICE)
    assert config.main_service() == AIRPLAY_SERVICE

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
    assert device_info.mac == "FF:EE:DD:CC:BB:AA"


# Mainly to test devices which are pure AirPlay devices/speakers
def test_raop_device_info(config):
    config.add_service(RAOP_SERVICE)

    device_info = config.device_info
    assert device_info.operating_system == OperatingSystem.TvOS
    assert device_info.version == "14.5"
    assert device_info.build_number is None
    assert device_info.model == DeviceModel.HomePodMini
    assert device_info.mac is None


def test_airport_express_info(config):
    config.add_service(AIRPORT_SERVICE)

    device_info = config.device_info
    assert device_info.operating_system == OperatingSystem.AirPortOS
    assert device_info.version is None
    assert device_info.build_number is None
    assert device_info.model == DeviceModel.AirPortExpressGen2
    assert device_info.mac is None


def test_airport_express_extra_properties():
    extra_properties = {
        # MAC, raMA=2.4GHz MAC, raM2=5GHz MAC
        "wama": "AA-AA-AA-AA-AA-AA,raMA=BB-BB-BB-BB-BB-BB,raM2=CC-CC-CC-CC-CC-CC,"
        + "raNm=MySsid,raCh=11,rCh2=112,raSt=1,raNA=0,syFl=0x80C,syAP=115,syVs=7.8.1,"
        + "srcv=78100.3,bjSd=2"
    }
    config = conf.AppleTV(ADDRESS_1, NAME, deep_sleep=True, properties=extra_properties)
    config.add_service(AIRPORT_SERVICE)

    device_info = config.device_info
    assert device_info.operating_system == OperatingSystem.AirPortOS
    assert device_info.version == "7.8.1"
    assert device_info.build_number is None
    assert device_info.model == DeviceModel.AirPortExpressGen2
    assert device_info.mac == "AA:AA:AA:AA:AA:AA"


@pytest.mark.parametrize(
    "service,expected",
    [
        (DMAP_SERVICE, True),
        (MRP_SERVICE, True),
        (AIRPLAY_SERVICE, True),
        (COMPANION_SERVICE, False),
        (RAOP_SERVICE, True),
    ],
)
def test_ready(config, service, expected):
    assert not config.ready

    config.add_service(service)
    assert config.ready == expected


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
