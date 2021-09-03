"""Unit tests for pyatv.airplay."""
from ipaddress import ip_address

from deepdiff import DeepDiff
import pytest

from pyatv.airplay import device_info, scan
from pyatv.const import DeviceModel
from pyatv.interface import DeviceInfo
from pyatv.support import mdns

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
    "properties,expected",
    [
        ({"model": "unknown"}, {}),
        ({"model": "AppleTV6,2"}, {DeviceInfo.MODEL: DeviceModel.Gen4K}),
        ({"osvers": "14.7"}, {DeviceInfo.VERSION: "14.7"}),
        ({"deviceid": "aa:bb:cc:dd:ee:ff"}, {DeviceInfo.MAC: "aa:bb:cc:dd:ee:ff"}),
    ],
)
def test_device_info(properties, expected):
    assert not DeepDiff(device_info(properties), expected)
