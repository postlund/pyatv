"""Unit tests for port knocker module."""

import asyncio
import errno
from ipaddress import ip_address
import sys
import time
import unittest
from unittest.mock import MagicMock, patch

import pytest

from pyatv.support.knock import knock, knocker

from tests.utils import until

LOCALHOST = ip_address("127.0.0.1")
LINK_LOCAL = ip_address("169.254.0.0")
MULTICAST_IP = ip_address("224.0.0.251")


@pytest.mark.asyncio
async def test_single_port_knock(knock_server):
    server = await knock_server()
    await knock(LOCALHOST, [server.port], 1)
    await until(lambda: server.got_knock)


@pytest.mark.asyncio
async def test_multi_port_knock(knock_server):
    server1 = await knock_server()
    server2 = await knock_server()
    await knock(LOCALHOST, [server1.port, server2.port], 1)
    await until(lambda: server1.got_knock)
    await until(lambda: server2.got_knock)


@pytest.mark.asyncio
async def test_continuous_knocking(knock_server):
    server = await knock_server()
    await knocker(LOCALHOST, [server.port], asyncio.get_running_loop(), timeout=6)
    # Knocking once should be enough as long as we let the connection
    # try to complete for a long enough time
    await until(lambda: server.count == 1)


@pytest.mark.asyncio
async def test_knock_does_not_raise(knock_server):
    server = await knock_server()
    task = await knocker(LOCALHOST, [1], asyncio.get_running_loop(), timeout=0.5)
    # Knocking on a non-listening port should not raise
    await task


@pytest.mark.asyncio
async def test_knock_times_out():
    task = await knocker(LINK_LOCAL, [1], asyncio.get_running_loop(), timeout=0.3)
    # Knocking on link-local will timeout and should not raise
    await task


@pytest.mark.asyncio
async def test_abort_knock_unreachable_host():
    start = time.monotonic()
    task = await knocker(MULTICAST_IP, [1], asyncio.get_running_loop(), timeout=3)
    # Knocking on the multicast ip will raise Network unreachable and should abort right away
    await task
    end = time.monotonic()
    assert (end - start) < 1


@pytest.mark.asyncio
@unittest.skipIf(sys.version_info < (3, 8), "Requires 3.8 or later to patch asyncio")
async def test_abort_knock_down_host(caplog):
    asyncio.get_running_loop().set_debug(True)
    start = time.monotonic()
    with patch(
        "pyatv.support.knock.asyncio.open_connection",
        side_effect=[
            (MagicMock(), MagicMock()),
            (MagicMock(), MagicMock()),
            OSError(errno.EHOSTDOWN, None),
            (MagicMock(), MagicMock()),
        ],
    ):
        task = await knocker(
            "127.0.0.1", [1, 2, 3, 4], asyncio.get_running_loop(), timeout=3
        )
        await task
    end = time.monotonic()
    assert (end - start) < 1
    await asyncio.sleep(0)
    asyncio.get_running_loop().set_debug(False)
    assert "Task exception was never retrieved" not in caplog.text


@pytest.mark.asyncio
@unittest.skipIf(sys.version_info < (3, 8), "Requires 3.8 or later to patch asyncio")
async def atest_abort_knock_unhandled_exception(caplog):
    loop = asyncio.get_running_loop()
    loop.set_debug(True)
    start = time.monotonic()
    with patch("pyatv.support.knock.asyncio.open_connection", side_effect=ValueError):
        task = await knocker("127.0.0.1", [1, 2, 3, 4], loop, timeout=3)
        # For unknown exceptions we want to s'till raise them
        with pytest.raises(ValueError):
            await task
    end = time.monotonic()
    assert (end - start) < 1
    await asyncio.sleep(0)
    loop.set_debug(False)
    assert "Task exception was never retrieved" not in caplog.text
