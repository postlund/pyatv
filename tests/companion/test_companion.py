"""Unit tests for pyatv.companion."""
from ipaddress import ip_address

from deepdiff import DeepDiff

from pyatv.companion import scan
from pyatv.support import mdns

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
