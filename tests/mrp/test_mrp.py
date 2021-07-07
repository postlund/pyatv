"""Unit tests for pyatv.mrp."""
from ipaddress import ip_address

from deepdiff import DeepDiff

from pyatv.mrp import scan
from pyatv.support import mdns

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
