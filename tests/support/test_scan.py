"""Unit tests for scan module."""

import pytest

from pyatv.support.mdns import Response, Service
from pyatv.support.scan import (
    HOMESHARING_SERVICE,
    DEVICE_SERVICE,
    MEDIAREMOTE_SERVICE,
    AIRPLAY_SERVICE,
    get_unique_identifiers,
)


HS = Service(HOMESHARING_SERVICE, "name", None, 0, {"hG": "hs_id"})
DEVICE = Service(DEVICE_SERVICE, "dev_id", None, 0, {})
MRP = Service(MEDIAREMOTE_SERVICE, "name", None, 0, {"UniqueIdentifier": "mrp_id"})
AIRPLAY = Service(AIRPLAY_SERVICE, "name", None, 0, {"deviceid": "airplay_id"})


@pytest.fixture
def response():
    yield Response([], False, None)


def test_unique_identifier_empty(response):
    assert len(list(get_unique_identifiers(response))) == 0


def test_unique_identifier_home_sharing(response):
    response.services.append(HS)

    identifiers = list(get_unique_identifiers(response))
    assert len(identifiers) == 1
    assert "hs_id" in identifiers


def test_unique_identifier_device(response):
    response.services.append(DEVICE)

    identifiers = list(get_unique_identifiers(response))
    assert len(identifiers) == 1
    assert "dev_id" in identifiers


def test_unique_identifier_mrp(response):
    response.services.append(MRP)

    identifiers = list(get_unique_identifiers(response))
    assert len(identifiers) == 1
    assert "mrp_id" in identifiers


def test_unique_identifier_airplay(response):
    response.services.append(AIRPLAY)

    identifiers = list(get_unique_identifiers(response))
    assert len(identifiers) == 1
    assert "airplay_id" in identifiers


def test_unique_identifier_multiple(response):
    response.services.append(HS)
    response.services.append(DEVICE)
    response.services.append(MRP)
    response.services.append(AIRPLAY)

    identifiers = list(get_unique_identifiers(response))
    assert len(identifiers) == 4
    assert "hs_id" in identifiers
    assert "dev_id" in identifiers
    assert "mrp_id" in identifiers
    assert "airplay_id" in identifiers
