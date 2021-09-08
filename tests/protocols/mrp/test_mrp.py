"""Unit tests for pyatv.protocols.mrp."""
from ipaddress import ip_address

from deepdiff import DeepDiff
import pytest

from pyatv.const import OperatingSystem
from pyatv.core import mdns
from pyatv.core.device_info import lookup_version
from pyatv.interface import DeviceInfo
from pyatv.protocols.mrp import device_info, scan

MRP_SERVICE = "_mediaremotetv._tcp.local"


def test_companion_scan_handlers_present():
    handlers = scan()
    assert len(handlers) == 1
    assert MRP_SERVICE in handlers


def test_mrp_handler_to_service():
    handler = scan()[MRP_SERVICE]

    mdns_service = mdns.Service(
        MRP_SERVICE, "foo", ip_address("127.0.0.1"), 1234, {"Name": "test"}
    )
    mdns_response = mdns.Response([], False, None)

    name, service = handler(mdns_service, mdns_response)
    assert name == "test"
    assert service.port == 1234
    assert service.credentials is None
    assert not DeepDiff(service.properties, {"Name": "test"})


@pytest.mark.parametrize(
    "properties,expected",
    [
        (
            {"systembuildversion": "unknown"},
            {
                DeviceInfo.BUILD_NUMBER: "unknown",
                DeviceInfo.OPERATING_SYSTEM: OperatingSystem.TvOS,
            },
        ),
        (
            {"systembuildversion": "18M60"},
            {
                DeviceInfo.BUILD_NUMBER: "18M60",
                DeviceInfo.VERSION: "14.7",
                DeviceInfo.OPERATING_SYSTEM: OperatingSystem.TvOS,
            },
        ),
        (
            {"macaddress": "aa:bb:cc:dd:ee:ff"},
            {
                DeviceInfo.MAC: "aa:bb:cc:dd:ee:ff",
                DeviceInfo.OPERATING_SYSTEM: OperatingSystem.TvOS,
            },
        ),
    ],
)
def test_device_info(properties, expected):
    assert not DeepDiff(device_info(properties), expected)
