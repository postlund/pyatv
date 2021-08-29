"""Functional tests for helper methods. Agnostic to protocol implementation."""

from unittest.mock import MagicMock, patch

import pytest

from pyatv import conf, helpers

from tests.utils import data_path


@pytest.fixture
def mock_scan():
    atvs = []
    with patch("pyatv.scan") as _mock_scan:

        async def _scan(*args, **kwargs):
            return atvs

        _mock_scan.side_effect = _scan
        yield atvs


@pytest.fixture
def mock_connect():
    with patch("pyatv.connect") as _mock_connect:
        yield _mock_connect


@pytest.mark.asyncio
async def test_auto_connect_with_no_device(mock_scan):
    obj = MagicMock()
    obj.found = True

    async def found_handler():
        assert False, "should not be called"

    async def not_found_handler():
        obj.found = False

    await helpers.auto_connect(found_handler, not_found=not_found_handler)

    assert not obj.found


@pytest.mark.asyncio
async def test_auto_connect_with_device(mock_scan, mock_connect):
    obj = MagicMock()
    obj.found = None
    obj.closed = False

    def _close():
        obj.closed = True

    config = conf.AppleTV("address", "name")
    mock_device = MagicMock()

    mock_scan.append(config)

    async def _connect(*arsgs):
        return mock_device

    mock_connect.side_effect = _connect

    async def found_handler(atv):
        obj.found = atv

    await helpers.auto_connect(found_handler)

    assert obj.found == mock_device
    mock_device.close.assert_called_once()


@pytest.mark.parametrize(
    "service_type,service_name,properties,expected_id",
    [
        ("_unknown._tcp.local", "name", {}, None),
        ("_appletv-v2._tcp.local", "name", {}, "name"),
        ("_appletv-v2._tcp.local", "name_duplicate", {}, "name"),
        ("_touch-able._tcp.local", "name", {}, "name"),
        ("_touch-able._tcp.local", "name_duplicate", {}, "name"),
        ("_mediaremotetv._tcp.local", "name", {"UniqueIdentifier": "test"}, "test"),
        ("_airplay._tcp.local", "name", {"deviceid": "test"}, "test"),
        ("_raop._tcp.local", "abcd@name", {}, "abcd"),
        ("_raop._tcp.local", "abcd@name", {}, "abcd"),
        ("_hscp._tcp.local", "name", {"Machine ID": "abcd"}, "abcd"),
    ],
)
def test_get_unique_id_(service_type, service_name, properties, expected_id):
    assert helpers.get_unique_id(service_type, service_name, properties) == expected_id


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "test_file,streamable",
    [
        ("only_metadata.wav", True),
        ("README", False),
    ],
)
async def test_is_streamable_supported_file(test_file, streamable):
    assert await helpers.is_streamable(data_path(test_file)) == streamable
