"""Unit tests for pyatv.protocols.mrp."""

from ipaddress import ip_address

from deepdiff import DeepDiff
import pytest

from pyatv.const import OperatingSystem, PairingRequirement, Protocol
from pyatv.core import MutableService, mdns
from pyatv.interface import DeviceInfo
from pyatv.protocols.mrp import device_info, scan, service_info
from pyatv.support.device_info import lookup_version

MRP_SERVICE = "_mediaremotetv._tcp.local"


def test_companion_scan_handlers_present():
    handlers = scan()
    assert len(handlers) == 1
    assert MRP_SERVICE in handlers


def test_mrp_handler_to_service():
    handler, _ = scan()[MRP_SERVICE]

    mdns_service = mdns.Service(
        MRP_SERVICE, "foo", ip_address("127.0.0.1"), 1234, {"Name": "test"}
    )
    mdns_response = mdns.Response([], False, None)

    name, service = handler(mdns_service, mdns_response)
    assert name == "test"
    assert service.port == 1234
    assert service.credentials is None
    assert not DeepDiff(service.properties, {"Name": "test"})


def test_mrp_device_info_name():
    _, device_info_name = scan()[MRP_SERVICE]
    assert device_info_name("Ohana") == "Ohana"


@pytest.mark.parametrize(
    "service_type,properties,expected",
    [
        (
            "_dummy._tcp.local",
            {"systembuildversion": "unknown"},
            {
                DeviceInfo.BUILD_NUMBER: "unknown",
                DeviceInfo.OPERATING_SYSTEM: OperatingSystem.TvOS,
            },
        ),
        (
            "_dummy._tcp.local",
            {"systembuildversion": "18M60"},
            {
                DeviceInfo.BUILD_NUMBER: "18M60",
                DeviceInfo.VERSION: "14.7",
                DeviceInfo.OPERATING_SYSTEM: OperatingSystem.TvOS,
            },
        ),
        (
            "_dummy._tcp.local",
            {"macaddress": "aa:bb:cc:dd:ee:ff"},
            {
                DeviceInfo.MAC: "aa:bb:cc:dd:ee:ff",
                DeviceInfo.OPERATING_SYSTEM: OperatingSystem.TvOS,
            },
        ),
    ],
)
def test_device_info(service_type, properties, expected):
    assert not DeepDiff(device_info(service_type, properties), expected)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mrp_props,airplay_props,pairing_req",
    [
        ({}, {}, PairingRequirement.Disabled),
        ({}, {"allowpairing": "YES"}, PairingRequirement.Disabled),
        ({"allowpairing": "yes"}, {}, PairingRequirement.Optional),
        ({"allowpairing": "YES"}, {}, PairingRequirement.Optional),
        ({"allowpairing": "no"}, {}, PairingRequirement.Disabled),
    ],
)
async def test_service_info_pairing(airplay_props, mrp_props, pairing_req):
    mrp_service = MutableService("mrp", Protocol.MRP, 0, mrp_props)
    airplay_service = MutableService("id", Protocol.AirPlay, 0, airplay_props)

    assert mrp_service.pairing == PairingRequirement.Unsupported
    assert airplay_service.pairing == PairingRequirement.Unsupported

    await service_info(
        mrp_service,
        DeviceInfo({}),
        {Protocol.MRP: mrp_service, Protocol.AirPlay: airplay_service},
    )

    assert mrp_service.pairing == pairing_req
    assert airplay_service.pairing == PairingRequirement.Unsupported


@pytest.mark.asyncio
async def test_disabled_service_no_pairing():
    mrp_service = MutableService("mrp", Protocol.MRP, 0, {}, enabled=False)
    airplay_service = MutableService("id", Protocol.AirPlay, 0, {"allowpairing": "no"})

    await service_info(
        mrp_service,
        DeviceInfo({}),
        {Protocol.MRP: mrp_service, Protocol.AirPlay: airplay_service},
    )
    assert mrp_service.pairing == PairingRequirement.NotNeeded
