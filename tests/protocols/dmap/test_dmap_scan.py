"""Functional tests for DMAP scan."""
from ipaddress import ip_address

import pytest

import pyatv
from pyatv import conf
from pyatv.const import Protocol

from tests import fake_udns
from tests.conftest import Scanner
from tests.utils import assert_device

IP_1 = "10.0.0.1"

DMAP_SERVICE_NAME = "DMAP service"
DMAP_NAME = "DMAP ATV"
DMAP_HSGID = "hsgid"

pytestmark = pytest.mark.asyncio


async def test_multicast_scan_home_sharing_merge(udns_server, multicast_scan):
    udns_server.add_service(
        fake_udns.device_service(DMAP_SERVICE_NAME, DMAP_NAME, addresses=[IP_1])
    )
    udns_server.add_service(
        fake_udns.homesharing_service(
            DMAP_SERVICE_NAME, DMAP_NAME, DMAP_HSGID, addresses=[IP_1]
        )
    )

    atvs = await multicast_scan()
    assert len(atvs) == 1

    assert_device(
        atvs[0],
        DMAP_NAME,
        ip_address(IP_1),
        DMAP_SERVICE_NAME,
        Protocol.DMAP,
        3689,
        DMAP_HSGID,
    )


async def test_multicast_scan_home_sharing_merge(udns_server, multicast_scan):
    udns_server.add_service(
        fake_udns.device_service(DMAP_SERVICE_NAME, DMAP_NAME, addresses=[IP_1])
    )
    udns_server.add_service(
        fake_udns.homesharing_service(
            DMAP_SERVICE_NAME, DMAP_NAME, DMAP_HSGID, addresses=[IP_1]
        )
    )

    atvs = await multicast_scan()
    assert len(atvs) == 1

    assert_device(
        atvs[0],
        DMAP_NAME,
        ip_address(IP_1),
        DMAP_SERVICE_NAME,
        Protocol.DMAP,
        3689,
        DMAP_HSGID,
    )


async def test_multicast_scan_hscp_device(udns_server, multicast_scan):
    udns_server.add_service(
        fake_udns.hscp_service(
            DMAP_NAME, DMAP_SERVICE_NAME, DMAP_HSGID, addresses=[IP_1], port=3689
        )
    )

    atvs = await multicast_scan()
    assert len(atvs) == 1
    assert_device(
        atvs[0],
        DMAP_NAME,
        ip_address(IP_1),
        DMAP_SERVICE_NAME,
        Protocol.DMAP,
        3689,
        DMAP_HSGID,
    )


async def test_unicast_scan_homesharing(udns_server, unicast_scan):
    udns_server.add_service(
        fake_udns.homesharing_service(
            DMAP_SERVICE_NAME, DMAP_NAME, DMAP_HSGID, addresses=[IP_1]
        )
    )

    atvs = await unicast_scan()
    assert len(atvs) == 1

    assert_device(
        atvs[0],
        DMAP_NAME,
        ip_address(IP_1),
        DMAP_SERVICE_NAME,
        Protocol.DMAP,
        3689,
        DMAP_HSGID,
    )


async def test_unicast_scan_no_homesharing(udns_server, unicast_scan):
    udns_server.add_service(
        fake_udns.device_service(DMAP_SERVICE_NAME, DMAP_NAME, addresses=[IP_1])
    )

    atvs = await unicast_scan()
    assert len(atvs) == 1

    assert_device(
        atvs[0],
        DMAP_NAME,
        ip_address(IP_1),
        DMAP_SERVICE_NAME,
        Protocol.DMAP,
        3689,
    )


async def test_unicast_scan_hscp_device(udns_server, unicast_scan):
    udns_server.add_service(
        fake_udns.hscp_service(
            DMAP_NAME, DMAP_SERVICE_NAME, DMAP_HSGID, addresses=[IP_1], port=3689
        )
    )

    atvs = await unicast_scan()
    assert len(atvs) == 1
    assert_device(
        atvs[0],
        DMAP_NAME,
        ip_address(IP_1),
        DMAP_SERVICE_NAME,
        Protocol.DMAP,
        3689,
        DMAP_HSGID,
    )
