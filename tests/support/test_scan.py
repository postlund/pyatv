"""Unit tests for scan module."""

import pytest

from pyatv.support.mdns import Response, Service
from pyatv.support.scan import (
    AIRPLAY_SERVICE,
    COMPANION_SERVICE,
    DEVICE_SERVICE,
    HOMESHARING_SERVICE,
    MEDIAREMOTE_SERVICE,
    RAOP_SERVICE,
    get_unique_identifiers,
)

HS = Service(HOMESHARING_SERVICE, "hsname", None, 0, {"hG": "hs_id"})
DEVICE = Service(DEVICE_SERVICE, "devid", None, 0, {})
MRP = Service(MEDIAREMOTE_SERVICE, "name", None, 0, {"UniqueIdentifier": "mrp_id"})
AIRPLAY = Service(AIRPLAY_SERVICE, "name", None, 0, {"deviceid": "airplay_id"})
COMPANION = Service(COMPANION_SERVICE, "name", None, 0, {})
RAOP = Service(RAOP_SERVICE, "raop_id@name", None, 0, {})


@pytest.fixture
def response():
    yield Response([], False, None)


def test_unique_identifier_empty(response):
    assert len(list(get_unique_identifiers(response))) == 0


def test_unique_identifier_home_sharing(response):
    response.services.append(HS)

    identifiers = list(get_unique_identifiers(response))
    assert len(identifiers) == 1
    assert "hsname" in identifiers


def test_unique_identifier_device(response):
    response.services.append(DEVICE)

    identifiers = list(get_unique_identifiers(response))
    assert len(identifiers) == 1
    assert "devid" in identifiers


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


def test_unique_identifier_raop(response):
    response.services.append(RAOP)

    identifiers = list(get_unique_identifiers(response))
    assert len(identifiers) == 1
    assert "raop_id" in identifiers


def test_unique_identifier_multiple(response):
    response.services.append(HS)
    response.services.append(DEVICE)
    response.services.append(MRP)
    response.services.append(AIRPLAY)
    response.services.append(COMPANION)
    response.services.append(RAOP)

    identifiers = list(get_unique_identifiers(response))
    assert len(identifiers) == 5
    assert "hsname" in identifiers
    assert "devid" in identifiers
    assert "mrp_id" in identifiers
    assert "airplay_id" in identifiers
    assert "raop_id" in identifiers
