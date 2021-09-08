"""Functional tests for Companion scanning.."""

from ipaddress import ip_address

import pytest

from pyatv.const import Protocol

from tests import fake_udns
from tests.conftest import Scanner

IP_1 = "10.0.0.1"

COMPANIOM_NAME = "Companion"
MRP_ID = "mrp_id_1"
MRP_SERVICE_NAME = "MRP Service"

COMPANION_PORT = 1234

pytestmark = pytest.mark.asyncio


async def test_multicast_scan_companion_device(udns_server, multicast_scan: Scanner):
    udns_server.add_service(
        fake_udns.companion_service(
            COMPANIOM_NAME, addresses=[IP_1], port=COMPANION_PORT
        )
    )

    atvs = await multicast_scan()
    assert len(atvs) == 0


# Companion does not have a unique id we can use, so it's not possible to discover
# on its own. It needs another protocol with an identifier and MRP is borrowed here,
# but any other protocol would do as well.
async def test_multicast_scan_mrp_with_companion(udns_server, multicast_scan: Scanner):
    udns_server.add_service(
        fake_udns.mrp_service(
            MRP_SERVICE_NAME, COMPANIOM_NAME, MRP_ID, addresses=[IP_1]
        )
    )
    udns_server.add_service(
        fake_udns.companion_service(
            COMPANIOM_NAME, addresses=[IP_1], port=COMPANION_PORT
        )
    )

    atvs = await multicast_scan()
    assert len(atvs) == 1

    dev = atvs[0]
    assert dev
    assert dev.name == COMPANIOM_NAME
    assert dev.get_service(Protocol.MRP)

    companion = dev.get_service(Protocol.Companion)
    assert companion
    assert companion.port == COMPANION_PORT


async def test_unicast_scan_comapnion(udns_server, unicast_scan: Scanner):
    udns_server.add_service(
        fake_udns.companion_service(COMPANIOM_NAME, IP_1, COMPANION_PORT)
    )

    atvs = await unicast_scan()
    assert len(atvs) == 0
