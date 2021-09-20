"""Unit tests for pyatv.conf."""

from deepdiff import DeepDiff
import pytest

from pyatv import exceptions
from pyatv.conf import AppleTV, ManualService
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
PASSWORD_1 = "password1"

TEST_PROPERTIES = {"_test._tcp.local": {"foo": "bar"}}

DMAP_SERVICE = ManualService(IDENTIFIER_1, Protocol.DMAP, PORT_1, {})
MRP_SERVICE = ManualService(IDENTIFIER_2, Protocol.MRP, PORT_2, TEST_PROPERTIES)
AIRPLAY_SERVICE = ManualService(IDENTIFIER_3, Protocol.AirPlay, PORT_1, {})
COMPANION_SERVICE = ManualService(None, Protocol.Companion, PORT_3, {})
RAOP_SERVICE = ManualService(IDENTIFIER_4, Protocol.RAOP, PORT_4, {})
AIRPORT_SERVICE = ManualService(IDENTIFIER_1, Protocol.RAOP, PORT_1, {})


@pytest.fixture
def config():
    yield AppleTV(ADDRESS_1, NAME, deep_sleep=True)


def test_address_and_name(config):
    assert config.address == ADDRESS_1
    assert config.name == NAME


def test_equality(config):
    assert config == config

    atv2 = AppleTV(ADDRESS_1, NAME)
    atv2.add_service(ManualService(IDENTIFIER_1, Protocol.AirPlay, PORT_1, {}))
    assert config != atv2


def test_properties():
    assert "_test._tcp.local" in MRP_SERVICE.properties
    assert MRP_SERVICE.properties["_test._tcp.local"] == {"foo": "bar"}


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
    config.add_service(ManualService(IDENTIFIER_1, Protocol.DMAP, 3689, {}, "LOGIN_ID"))
    config.add_service(ManualService(IDENTIFIER_2, Protocol.MRP, PORT_2, {}))

    # Check for some keywords to not lock up format too much
    output = str(config)
    assert ADDRESS_1 in output
    assert NAME in output
    assert "LOGIN_ID" in output
    assert str(PORT_2) in output
    assert "3689" in output
    assert "Deep Sleep: True" in output


def test_raop_password_in_str(config):
    config.add_service(
        ManualService(IDENTIFIER_1, Protocol.RAOP, 1234, {}, password=PASSWORD_1)
    )

    assert PASSWORD_1 in str(config)


@pytest.mark.parametrize(
    "password1,password2,expected",
    [
        ("pass1", None, "pass1"),
        (None, "pass2", "pass2"),
        ("pass2", "pass1", "pass1"),
    ],
)
def test_service_merge_password(password1, password2, expected):
    service1 = ManualService("id1", Protocol.DMAP, 0, {})
    service2 = ManualService("id2", Protocol.DMAP, 0, {})

    service1.password = password1
    service2.password = password2

    service1.merge(service2)

    assert service1.password == expected


@pytest.mark.parametrize(
    "creds1,creds2,expected",
    [
        ("creds1", None, "creds1"),
        (None, "creds2", "creds2"),
        ("creds2", "creds1", "creds1"),
    ],
)
def test_service_merge_credentials(creds1, creds2, expected):
    service1 = ManualService("id1", Protocol.DMAP, 0, {})
    service2 = ManualService("id2", Protocol.DMAP, 0, {})

    service1.credentials = creds1
    service2.credentials = creds2

    service1.merge(service2)

    assert service1.credentials == expected


@pytest.mark.parametrize(
    "props1,props2,expected",
    [
        ({"foo": "bar"}, None, {"foo": "bar"}),
        (None, {"foo": "bar"}, {"foo": "bar"}),
        (
            {"foo": "bar"},
            {"foo": "bar2", "test": "dummy"},
            {"foo": "bar2", "test": "dummy"},
        ),
    ],
)
def test_service_merge_properties(props1, props2, expected):
    service1 = ManualService("id1", Protocol.DMAP, 0, props1)
    service2 = ManualService("id2", Protocol.DMAP, 0, props2)

    service1.merge(service2)

    assert not DeepDiff(service1.properties, expected)
