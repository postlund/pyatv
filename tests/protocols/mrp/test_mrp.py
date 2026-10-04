"""Unit tests for pyatv.protocols.mrp."""

from ipaddress import ip_address

from deepdiff import DeepDiff
import pytest

from pyatv.const import OperatingSystem, PairingRequirement, PowerState, Protocol
from pyatv.core import MutableService, mdns
from pyatv.interface import DeviceInfo
from pyatv.protocols.mrp import (
    MrpPower,
    device_info,
    messages,
    protobuf,
    scan,
    service_info,
)
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


def _device_info(**fields):
    message = messages.create(protobuf.ProtocolMessage.DEVICE_INFO_MESSAGE)
    inner = protobuf.extract_inner(message)
    for name, value in fields.items():
        setattr(inner, name, value)
    return message


@pytest.mark.parametrize(
    "fields,expected",
    [
        ({"logicalDeviceCount": 1}, PowerState.On),
        ({"logicalDeviceCount": 0}, PowerState.Off),
        # The leader of a HomePod stereo pair reports zero logical devices
        # while it is playing, so the cluster fields have to decide it
        (
            {
                "logicalDeviceCount": 0,
                "deviceUID": "leader",
                "isClusterAware": True,
                "clusterLeaderID": "leader",
            },
            PowerState.On,
        ),
        # The other member of the pair is not the leader and stays off
        (
            {
                "logicalDeviceCount": 0,
                "deviceUID": "follower",
                "isClusterAware": True,
                "clusterLeaderID": "leader",
            },
            PowerState.Off,
        ),
        # An Apple TV that is asleep has no cluster fields at all
        ({"logicalDeviceCount": 0, "deviceUID": "atv"}, PowerState.Off),
    ],
)
def test_power_state_from_device_info(fields, expected):
    assert MrpPower._get_power_state(_device_info(**fields)) == expected
