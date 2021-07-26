"""Unit tests for pyatv.airplay."""
from ipaddress import ip_address

from deepdiff import DeepDiff

from pyatv.dmap import scan
from pyatv.support import mdns

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
    handler = scan()[HOMESHARING_SERVICE]

    mdns_service = mdns.Service(
        HOMESHARING_SERVICE, "foo", ip_address("127.0.0.1"), 1234, {"Name": "bar"}
    )
    mdns_response = mdns.Response([], False, None)

    name, service = handler(mdns_service, mdns_response)
    assert name == "bar"
    assert service.port == 1234
    assert service.credentials is None
    assert not DeepDiff(service.properties, {"Name": "bar"})


def test_dmap_handler_to_service():
    handler = scan()[DMAP_SERVICE]

    mdns_service = mdns.Service(
        DMAP_SERVICE, "foo", ip_address("127.0.0.1"), 1234, {"CtlN": "bar"}
    )
    mdns_response = mdns.Response([], False, None)

    name, service = handler(mdns_service, mdns_response)
    assert name == "bar"
    assert service.port == 1234
    assert service.credentials is None
    assert not DeepDiff(service.properties, {"CtlN": "bar"})
