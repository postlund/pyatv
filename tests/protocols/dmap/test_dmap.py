"""Unit tests for pyatv.protocols.dmap."""

from ipaddress import ip_address

from deepdiff import DeepDiff
import pytest

from pyatv.const import DeviceModel, OperatingSystem, PairingRequirement, Protocol
from pyatv.core import MutableService, mdns
from pyatv.interface import DeviceInfo
from pyatv.protocols.dmap import device_info, scan, service_info

HOMESHARING_SERVICE = "_appletv-v2._tcp.local"
DMAP_SERVICE = "_touch-able._tcp.local"
HSCP_SERVICE: str = "_hscp._tcp.local"


def test_dmap_scan_handlers_present():
    handlers = scan()
    assert len(handlers) == 3
    assert HOMESHARING_SERVICE in handlers
    assert DMAP_SERVICE in handlers
    assert HSCP_SERVICE in handlers


def test_homesharing_handler_to_service():
    handler, _ = scan()[HOMESHARING_SERVICE]

    mdns_service = mdns.Service(
        HOMESHARING_SERVICE, "foo", ip_address("127.0.0.1"), 1234, {"Name": "bar"}
    )
    mdns_response = mdns.Response([], False, None)

    name, service = handler(mdns_service, mdns_response)
    assert name == "bar"
    assert service.port == 1234
    assert service.credentials is None
    assert not DeepDiff(service.properties, {"Name": "bar"})


def test_homesharing_device_info_name():
    _, device_info_name = scan()[HOMESHARING_SERVICE]
    assert device_info_name("ANY") is None


def test_dmap_handler_to_service():
    handler, _ = scan()[DMAP_SERVICE]

    mdns_service = mdns.Service(
        DMAP_SERVICE, "foo", ip_address("127.0.0.1"), 1234, {"CtlN": "bar"}
    )
    mdns_response = mdns.Response([], False, None)

    name, service = handler(mdns_service, mdns_response)
    assert name == "bar"
    assert service.port == 1234
    assert service.credentials is None
    assert not DeepDiff(service.properties, {"CtlN": "bar"})


def test_dmap_device_info_name():
    _, device_info_name = scan()[DMAP_SERVICE]
    assert device_info_name("ANY") is None


@pytest.mark.parametrize(
    "service_type,properties,expected",
    [
        ("_foo._tcp.local", {}, {DeviceInfo.OPERATING_SYSTEM: OperatingSystem.Legacy}),
        (
            "_hscp._tcp.local",
            {},
            {
                DeviceInfo.OPERATING_SYSTEM: OperatingSystem.Legacy,
                DeviceInfo.MODEL: DeviceModel.Music,
            },
        ),
    ],
)
def test_device_info(service_type, properties, expected):
    assert not DeepDiff(device_info(service_type, properties), expected)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "dmap_props,mrp_props,pairing_req",
    [
        ({}, {}, PairingRequirement.Mandatory),
        ({"hg": "test"}, {}, PairingRequirement.Optional),
        ({}, {"hg": "test"}, PairingRequirement.Mandatory),
    ],
)
async def test_service_info_pairing(dmap_props, mrp_props, pairing_req):
    dmap_service = MutableService("id", Protocol.DMAP, 0, dmap_props)
    mrp_service = MutableService("mrp", Protocol.MRP, 0, mrp_props)

    assert dmap_service.pairing == PairingRequirement.Unsupported
    assert mrp_service.pairing == PairingRequirement.Unsupported

    await service_info(
        dmap_service,
        DeviceInfo({}),
        {Protocol.MRP: mrp_service, Protocol.DMAP: dmap_service},
    )

    assert dmap_service.pairing == pairing_req
    assert mrp_service.pairing == PairingRequirement.Unsupported
