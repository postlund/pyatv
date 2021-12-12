"""Unit tests for port knocker module."""

import asyncio
from ipaddress import ip_address

import pytest

from pyatv.support.knock import knock, knocker
from pyatv.support.net import unused_port

from tests.fake_knock import create_knock_server
from tests.utils import until

LOCALHOST = ip_address("127.0.0.1")


@pytest.mark.asyncio
async def test_single_port_knock(event_loop, knock_server):
    server = await knock_server()
    await knock(LOCALHOST, [server.port], 1)
    await until(lambda: server.got_knock)


@pytest.mark.asyncio
async def test_multi_port_knock(event_loop, knock_server):
    server1 = await knock_server()
    server2 = await knock_server()
    await knock(LOCALHOST, [server1.port, server2.port], 1)
    await until(lambda: server1.got_knock)
    await until(lambda: server2.got_knock)


@pytest.mark.asyncio
async def test_continuous_knocking(event_loop, knock_server):
    server = await knock_server()
    await knocker(LOCALHOST, [server.port], event_loop, timeout=6)
    # Knocking once should be enough as long as we let the connection
    # try to complete for a long enough time
    await until(lambda: server.count == 1)


@pytest.mark.asyncio
async def test_knock_does_not_raise(event_loop, knock_server):
    server = await knock_server()
    task = await knocker(LOCALHOST, [server.port + 1], event_loop, timeout=0.5)
    # Knocking on a non-listening port should not raise
    await task
