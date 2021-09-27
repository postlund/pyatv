"""Unit tests for pyatv.protocols.raop."""
from ipaddress import ip_address

from deepdiff import DeepDiff
import pytest

from pyatv.const import DeviceModel, PairingRequirement, Protocol
from pyatv.core import MutableService, mdns
from pyatv.interface import DeviceInfo
from pyatv.protocols.airplay.utils import AirPlayFlags
from pyatv.protocols.raop import device_info, scan, service_info

RAOP_SERVICE = "_raop._tcp.local"
AIRPORT_SERVICE = "_airport._tcp.local"


def test_raop_scan_handlers_present():
    handlers = scan()
    assert len(handlers) == 2
    assert RAOP_SERVICE in handlers


def test_raop_handler_to_service():
    handler = scan()[RAOP_SERVICE]

    mdns_service = mdns.Service(
        RAOP_SERVICE, "foo@bar", ip_address("127.0.0.1"), 1234, {"foo": "bar"}
    )
    mdns_response = mdns.Response([], False, None)

    name, service = handler(mdns_service, mdns_response)
    assert name == "bar"
    assert service.port == 1234
    assert service.credentials is None
    assert not DeepDiff(service.properties, {"foo": "bar"})


def test_airport_handler():
    handler = scan()[AIRPORT_SERVICE]

    mdns_service = mdns.Service(
        RAOP_SERVICE, "foo@bar", ip_address("127.0.0.1"), 1234, {"foo": "bar"}
    )
    mdns_response = mdns.Response([], False, None)

    assert not handler(mdns_service, mdns_response)


@pytest.mark.parametrize(
    "service_type,properties,expected",
    [
        ("_dummy._tcp.local", {"am": "unknown"}, {DeviceInfo.RAW_MODEL: "unknown"}),
        (
            "_dummy._tcp.local",
            {"am": "AppleTV6,2"},
            {DeviceInfo.MODEL: DeviceModel.Gen4K, DeviceInfo.RAW_MODEL: "AppleTV6,2"},
        ),
        ("_dummy._tcp.local", {"ov": "14.7"}, {DeviceInfo.VERSION: "14.7"}),
        # Special case for resolving MAC address and version on AirPort Express
        (
            "_dummy._tcp.local",
            {
                "wama": (
                    "AA-AA-AA-AA-AA-AA,"
                    "raMA=BB-BB-BB-BB-BB-BB,"
                    "raM2=CC-CC-CC-CC-CC-CC,"
                    "raNm=MyWifi,raCh=1,rCh2=2,"
                    "raSt=1,raNA=0,syFl=0x88C,"
                    "syAP=115,syVs=7.8.1,srcv=78100.3,bjSd=2"
                )
            },
            {
                DeviceInfo.MAC: "AA:AA:AA:AA:AA:AA",
                DeviceInfo.VERSION: "7.8.1",
            },
        ),
    ],
)
def test_device_info(service_type, properties, expected):
    assert not DeepDiff(device_info(service_type, properties), expected)


@pytest.mark.parametrize(
    "raop_props,mrp_props,requires_password",
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
async def test_service_info_password(raop_props, mrp_props, requires_password):
    raop_service = MutableService("id", Protocol.RAOP, 0, raop_props)
    mrp_service = MutableService("mrp", Protocol.MRP, 0, mrp_props)

    assert not raop_service.requires_password
    assert not mrp_service.requires_password

    await service_info(
        raop_service,
        DeviceInfo({}),
        {Protocol.MRP: mrp_service, Protocol.RAOP: raop_service},
    )

    assert raop_service.requires_password == requires_password
    assert not mrp_service.requires_password


@pytest.mark.parametrize(
    "raop_props,devinfo,pairing_req",
    [
        ({"sf": "0x200"}, {}, PairingRequirement.Mandatory),
        ({"flags": "0x200"}, {}, PairingRequirement.Mandatory),
        (
            {"features": hex(AirPlayFlags.SupportsLegacyPairing)},
            {},
            PairingRequirement.Mandatory,
        ),
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
async def test_service_info_pairing(raop_props, devinfo, pairing_req):
    raop_service = MutableService("id", Protocol.RAOP, 0, raop_props)

    assert raop_service.pairing == PairingRequirement.Unsupported

    await service_info(
        raop_service,
        DeviceInfo(devinfo),
        {Protocol.RAOP: raop_service},
    )

    assert raop_service.pairing == pairing_req


async def test_service_info_pairing_acl():
    raop_service = MutableService("id", Protocol.RAOP, 0, {})
    airplay_props = MutableService("id", Protocol.AirPlay, 0, {"acl": "1"})

    await service_info(
        raop_service,
        DeviceInfo({}),
        {Protocol.RAOP: raop_service, Protocol.AirPlay: airplay_props},
    )

    assert raop_service.pairing == PairingRequirement.Disabled
