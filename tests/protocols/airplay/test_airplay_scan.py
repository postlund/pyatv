"""Scanning tests with fake mDNS responder.."""

from ipaddress import ip_address

import pytest

from pyatv.const import Protocol

from tests import fake_udns
from tests.conftest import Scanner
from tests.utils import assert_device

IP_1 = "10.0.0.1"

AIRPLAY_NAME = "AirPlay ATV"
AIRPLAY_ID = "AA:BB:CC:DD:EE:FF"

pytestmark = pytest.mark.asyncio


async def test_multicast_scan_airplay_device(udns_server, multicast_scan: Scanner):
    udns_server.add_service(
        fake_udns.airplay_service(AIRPLAY_NAME, AIRPLAY_ID, addresses=[IP_1])
    )

    atvs = await multicast_scan()
    assert len(atvs) == 1
    assert atvs[0].name == AIRPLAY_NAME
    assert atvs[0].identifier == AIRPLAY_ID
    assert atvs[0].address == ip_address(IP_1)


async def test_unicast_scan_airplay(udns_server, unicast_scan: Scanner):
    udns_server.add_service(
        fake_udns.airplay_service(AIRPLAY_NAME, AIRPLAY_ID, addresses=[IP_1], port=7000)
    )

    atvs = await unicast_scan()
    assert len(atvs) == 1

    assert_device(
        atvs[0],
        AIRPLAY_NAME,
        ip_address(IP_1),
        AIRPLAY_ID,
        Protocol.AirPlay,
        7000,
    )
