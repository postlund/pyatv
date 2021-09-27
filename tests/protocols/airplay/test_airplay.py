"""Unit tests for pyatv.protocols.airplay."""
from ipaddress import ip_address

from deepdiff import DeepDiff
import pytest

from pyatv.const import DeviceModel, PairingRequirement, Protocol
from pyatv.core import MutableService, mdns
from pyatv.interface import DeviceInfo
from pyatv.protocols.airplay import device_info, scan, service_info
from pyatv.protocols.airplay.utils import AirPlayFlags

AIRPLAY_SERVICE = "_airplay._tcp.local"


def test_airplay_scan_handlers_present():
    handlers = scan()
    assert len(handlers) == 1
    assert AIRPLAY_SERVICE in handlers


def test_airplay_handler_to_service():
    handler = scan()[AIRPLAY_SERVICE]

    mdns_service = mdns.Service(
        AIRPLAY_SERVICE, "foo", ip_address("127.0.0.1"), 1234, {"foo": "bar"}
    )
    mdns_response = mdns.Response([], False, None)

    name, service = handler(mdns_service, mdns_response)
    assert name == "foo"
    assert service.port == 1234
    assert service.credentials is None
    assert not DeepDiff(service.properties, {"foo": "bar"})


@pytest.mark.parametrize(
    "service_type,properties,expected",
    [
        ("_dummy._tcp.local", {"model": "unknown"}, {DeviceInfo.RAW_MODEL: "unknown"}),
        (
            "_dummy._tcp.local",
            {"model": "AppleTV6,2"},
            {DeviceInfo.MODEL: DeviceModel.Gen4K, DeviceInfo.RAW_MODEL: "AppleTV6,2"},
        ),
        ("_dummy._tcp.local", {"osvers": "14.7"}, {DeviceInfo.VERSION: "14.7"}),
        (
            "_dummy._tcp.local",
            {"deviceid": "aa:bb:cc:dd:ee:ff"},
            {DeviceInfo.MAC: "aa:bb:cc:dd:ee:ff"},
        ),
    ],
)
def test_device_info(service_type, properties, expected):
    assert not DeepDiff(device_info(service_type, properties), expected)


@pytest.mark.parametrize(
    "airplay_props,mrp_props,requires_password",
    [
        ({}, {}, False),
        ({}, {"pw": "true"}, False),
        ({"pw": "true"}, {}, True),
        ({"pw": "TRUE"}, {}, True),
        ({"sf": "0x80"}, {}, True),
        ({}, {"sf": "0x80"}, False),
        ({"flags": "0x80"}, {}, True),
        ({}, {"flags": "0x80"}, False),
    ],
)
async def test_service_info_password(airplay_props, mrp_props, requires_password):
    airplay_service = MutableService("id", Protocol.AirPlay, 0, airplay_props)
    mrp_service = MutableService("mrp", Protocol.MRP, 0, mrp_props)

    assert not airplay_service.requires_password
    assert not mrp_service.requires_password

    await service_info(
        airplay_service,
        DeviceInfo({}),
        {Protocol.MRP: mrp_service, Protocol.AirPlay: airplay_service},
    )

    assert airplay_service.requires_password == requires_password
    assert not mrp_service.requires_password


@pytest.mark.parametrize(
    "airplay_props,devinfo,pairing_req",
    [
        ({"sf": "0x200"}, {}, PairingRequirement.Mandatory),
        ({"flags": "0x200"}, {}, PairingRequirement.Mandatory),
        (
            {"features": hex(AirPlayFlags.SupportsLegacyPairing)},
            {},
            PairingRequirement.Mandatory,
        ),
        ({"acl": "1"}, {}, PairingRequirement.Disabled),
        ({"acl": "1", "sf": "0x200"}, {}, PairingRequirement.Disabled),
        # Special cases for devices only requiring transient pairing, e.g.
        # HomePod and AirPort Express
        # AirPort Express gen 1 does not support AirPlay 2 => assume checks above
        (
            {"flags": "0x200"},
            {DeviceInfo.MODEL: DeviceModel.AirPortExpressGen2},
            PairingRequirement.NotNeeded,
        ),
        (
            {"flags": "0x200"},
            {DeviceInfo.MODEL: DeviceModel.HomePod},
            PairingRequirement.NotNeeded,
        ),
        (
            {"flags": "0x200"},
            {DeviceInfo.MODEL: DeviceModel.HomePodMini},
            PairingRequirement.NotNeeded,
        ),
    ],
)
async def test_service_info_pairing(airplay_props, devinfo, pairing_req):
    airplay_service = MutableService("id", Protocol.AirPlay, 0, airplay_props)

    assert airplay_service.pairing == PairingRequirement.Unsupported

    await service_info(
        airplay_service,
        DeviceInfo(devinfo),
        {Protocol.AirPlay: airplay_service},
    )

    assert airplay_service.pairing == pairing_req
