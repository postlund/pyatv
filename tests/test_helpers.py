"""Functional tests for helper methods. Agnostic to protocol implementation."""

from unittest.mock import MagicMock, patch

import pytest

from pyatv import conf, helpers


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
