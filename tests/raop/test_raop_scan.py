"""Functional tests for RAOP scanning.."""

from ipaddress import ip_address

import pytest

from pyatv.const import Protocol

from tests import fake_udns
from tests.conftest import Scanner
from tests.utils import assert_device

IP_1 = "10.0.0.1"

RAOP_ID = "AABBCCDDEEFF"
RAOP_NAME = "RAOP ATV"

RAOP_PORT = 4567

pytestmark = pytest.mark.asyncio


async def test_multicast_scan_raop_device(udns_server, multicast_scan):
    udns_server.add_service(
        fake_udns.raop_service(RAOP_NAME, RAOP_ID, addresses=[IP_1], port=RAOP_PORT)
    )

    atvs = await multicast_scan()
    assert len(atvs) == 1

    assert_device(
        atvs[0], RAOP_NAME, ip_address(IP_1), RAOP_ID, Protocol.RAOP, RAOP_PORT
    )


async def test_unicast_scan_raop(udns_server, unicast_scan):
    udns_server.add_service(
        fake_udns.raop_service(RAOP_NAME, RAOP_ID, addresses=[IP_1], port=RAOP_PORT)
    )

    atvs = await unicast_scan()
    assert len(atvs) == 1

    assert_device(
        atvs[0], RAOP_NAME, ip_address(IP_1), RAOP_ID, Protocol.RAOP, RAOP_PORT
    )
