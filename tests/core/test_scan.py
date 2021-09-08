"""Unit tests for scan module."""

from unittest.mock import patch

import pytest

from pyatv.core.mdns import Response, Service
from pyatv.core.scan import BaseScanner, get_unique_identifiers

TEST_SERVICE1 = Service("_service1._tcp.local", "service1", None, 0, {"a": "b"})
TEST_SERVICE2 = Service("_service2._tcp.local", "service2", None, 0, {"c": "d"})


@pytest.fixture
def response():
    yield Response([], False, None)


def test_unique_identifier_empty(response):
    assert len(list(get_unique_identifiers(response))) == 0


@patch("pyatv.core.scan.get_unique_id")
def test_unique_identifiers(unique_id_mock, response):
    response.services.append(TEST_SERVICE1)
    response.services.append(TEST_SERVICE2)

    unique_id_mock.side_effect = ["id1", "id2"]

    identifiers = get_unique_identifiers(response)

    assert "id1" == next(identifiers)
    unique_id_mock.assert_called_with("_service1._tcp.local", "service1", {"a": "b"})
    assert "id2" == next(identifiers)
    unique_id_mock.assert_called_with("_service2._tcp.local", "service2", {"c": "d"})
    assert not next(identifiers, None)
