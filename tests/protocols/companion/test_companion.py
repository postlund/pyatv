"""Unit tests for pyatv.protocols.companion."""
from ipaddress import ip_address

from deepdiff import DeepDiff
import pytest

from pyatv.const import DeviceModel, PairingRequirement, Protocol
from pyatv.core import MutableService, mdns
from pyatv.interface import DeviceInfo
from pyatv.protocols.companion import device_info, scan, service_info

COMPANION_SERVICE = "_companion-link._tcp.local"


def test_companion_scan_handlers_present():
    handlers = scan()
    assert len(handlers) == 1
    assert COMPANION_SERVICE in handlers


def test_companion_handler_to_service():
    handler = scan()[COMPANION_SERVICE]

    mdns_service = mdns.Service(
        COMPANION_SERVICE, "foo", ip_address("127.0.0.1"), 1234, {"foo": "bar"}
    )
    mdns_response = mdns.Response([], False, None)

    name, service = handler(mdns_service, mdns_response)
    assert name == "foo"
    assert service.port == 1234
    assert service.credentials is None
    assert not DeepDiff(service.properties, {"foo": "bar"})


@pytest.mark.parametrize(
    "properties,expected",
    [
        ({"rpmd": "unknown"}, {}),
        ({"rpmd": "AppleTV6,2"}, {DeviceInfo.MODEL: DeviceModel.Gen4K}),
    ],
)
def test_device_info(properties, expected):
    assert not DeepDiff(device_info(properties), expected)


async def test_service_info_pairing():
    service = MutableService(None, Protocol.Companion, 0, {})

    assert service.pairing == PairingRequirement.Unsupported
    await service_info(service, DeviceInfo({}), {Protocol.Companion: service})
    assert service.pairing == PairingRequirement.Mandatory
