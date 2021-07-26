"""Functional tests for MRP scanning.."""

from ipaddress import ip_address

import pytest

from pyatv.const import DeviceModel, Protocol

from tests import fake_udns
from tests.conftest import Scanner
from tests.utils import assert_device

IP_1 = "10.0.0.1"

MRP_ID = "mrp_id_1"
MRP_NAME = "MRP ATV"
MRP_SERVICE_NAME = "MRP Service"

MRP_PORT = 49152

pytestmark = pytest.mark.asyncio


async def test_multicast_scan_mrp_with_companion(udns_server, multicast_scan):
    udns_server.add_service(
        fake_udns.mrp_service(
            MRP_SERVICE_NAME, MRP_NAME, MRP_ID, addresses=[IP_1], port=MRP_PORT
        )
    )

    atvs = await multicast_scan(protocol=Protocol.MRP)
    assert len(atvs) == 1

    assert_device(atvs[0], MRP_NAME, ip_address(IP_1), MRP_ID, Protocol.MRP, MRP_PORT)


async def test_unicast_scan_mrp(udns_server, unicast_scan):
    udns_server.add_service(
        fake_udns.mrp_service(
            MRP_SERVICE_NAME, MRP_NAME, MRP_ID, addresses=[IP_1], port=MRP_PORT
        )
    )

    atvs = await unicast_scan()
    assert len(atvs) == 1

    assert_device(atvs[0], MRP_NAME, ip_address(IP_1), MRP_ID, Protocol.MRP, MRP_PORT)
