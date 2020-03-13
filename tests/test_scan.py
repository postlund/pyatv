"""Functional tests using the API with a fake Apple TV."""

import pyatv
import ipaddress

from unittest.mock import patch

import pytest

from pyatv.const import Protocol
from tests import fake_udns, zeroconf_stub


IP_1 = "10.0.0.1"
IP_2 = "10.0.0.2"
IP_3 = "10.0.0.3"
IP_4 = "10.0.0.4"
IP_5 = "10.0.0.5"
IP_6 = "10.0.0.6"
IP_LOCALHOST = "127.0.0.1"

HSGID = "hsgid"

MRP_ID_1 = "mrp_id_1"
MRP_ID_2 = "mrp_id_2"

AIRPLAY_ID = "AA:BB:CC:DD:EE:FF"

HOMESHARING_SERVICE_1 = zeroconf_stub.homesharing_service(
    "AAAA", b"Apple TV 1", IP_1, b"aaaa"
)
HOMESHARING_SERVICE_2 = zeroconf_stub.homesharing_service(
    "BBBB", b"Apple TV 2", IP_2, b"bbbb"
)
HOMESHARING_SERVICE_3 = zeroconf_stub.homesharing_service(
    "CCCC", b"Apple TV\xC2\xA03", IP_3, b"cccc"
)
DEVICE_SERVICE_1 = zeroconf_stub.device_service("CCCC", b"Apple TV\xC2\xA03", IP_3)
MRP_SERVICE_1 = zeroconf_stub.mrp_service("DDDD", b"Apple TV 4", IP_4, MRP_ID_1)
MRP_SERVICE_2 = zeroconf_stub.mrp_service("EEEE", b"Apple TV 5", IP_5, MRP_ID_2)
AIRPLAY_SERVICE_1 = zeroconf_stub.airplay_service("Apple TV 6", IP_6, AIRPLAY_ID)
AIRPLAY_SERVICE_2 = zeroconf_stub.airplay_service("Apple TV 4", IP_4, AIRPLAY_ID)


def _get_atv(atvs, ip):
    for atv in atvs:
        if atv.address == ipaddress.ip_address(ip):
            return atv
    return None


def assert_device(atv, name, address, identifier, protocol, port, creds=None):
    assert atv.name == name
    assert atv.address == address
    assert atv.identifier == identifier
    assert atv.get_service(protocol)
    assert atv.get_service(protocol).port == port
    assert atv.get_service(protocol).credentials == creds


@pytest.fixture
async def udns_server(event_loop):
    server = fake_udns.FakeUdns(event_loop)
    await server.start()
    yield server
    server.close()


@pytest.fixture
async def udns_scan(event_loop, udns_server):
    async def _scan():
        port = str(udns_server.port)
        with patch.dict("os.environ", {"PYATV_UDNS_PORT": port}):
            return await pyatv.scan(event_loop, hosts=[IP_LOCALHOST])

    yield _scan


@pytest.mark.asyncio
async def test_zeroconf_scan_no_device_found(event_loop):
    zeroconf_stub.stub(pyatv)

    atvs = await pyatv.scan(event_loop, timeout=0)
    assert len(atvs) == 0


@pytest.mark.asyncio
async def test_zeroconf_scan(event_loop):
    zeroconf_stub.stub(
        pyatv,
        HOMESHARING_SERVICE_1,
        HOMESHARING_SERVICE_2,
        MRP_SERVICE_1,
        AIRPLAY_SERVICE_1,
    )

    atvs = await pyatv.scan(event_loop, timeout=0)
    assert len(atvs) == 3

    # First device
    dev1 = _get_atv(atvs, IP_1)
    assert dev1
    assert dev1.identifier == "AAAA"

    # Second device
    dev2 = _get_atv(atvs, IP_2)
    assert dev2
    assert dev2.identifier == "BBBB"

    # Third device
    dev3 = _get_atv(atvs, IP_4)
    assert dev3
    assert dev3.identifier == MRP_ID_1


@pytest.mark.asyncio
async def test_zeroconf_scan_no_home_sharing(event_loop):
    zeroconf_stub.stub(pyatv, DEVICE_SERVICE_1)

    atvs = await pyatv.scan(event_loop, timeout=0)
    assert len(atvs) == 1
    assert atvs[0].name == "Apple TV 3"
    assert atvs[0].address == ipaddress.ip_address(IP_3)

    atv = atvs[0]
    assert atv.get_service(Protocol.DMAP).port == 3689


@pytest.mark.asyncio
async def test_zeroconf_scan_home_sharing_merge(event_loop):
    zeroconf_stub.stub(pyatv, DEVICE_SERVICE_1, HOMESHARING_SERVICE_3)

    atvs = await pyatv.scan(event_loop, timeout=0)
    assert len(atvs) == 1
    assert atvs[0].name == "Apple TV 3"
    assert atvs[0].address == ipaddress.ip_address("10.0.0.3")

    service = atvs[0].main_service()
    assert service.credentials == "cccc"
    assert service.port == 3689


@pytest.mark.asyncio
async def test_zeroconf_scan_mrp(event_loop):
    zeroconf_stub.stub(pyatv, MRP_SERVICE_1, MRP_SERVICE_2, DEVICE_SERVICE_1)

    atvs = await pyatv.scan(event_loop, timeout=0, protocol=Protocol.MRP)
    assert len(atvs) == 2

    dev1 = _get_atv(atvs, IP_4)
    assert dev1
    assert dev1.name == "Apple TV 4"
    assert dev1.get_service(Protocol.MRP)

    dev2 = _get_atv(atvs, IP_5)
    assert dev2
    assert dev2.name == "Apple TV 5"
    assert dev2.get_service(Protocol.MRP)


@pytest.mark.asyncio
async def test_zeroconf_scan_airplay_device(event_loop):
    zeroconf_stub.stub(pyatv, AIRPLAY_SERVICE_1)

    atvs = await pyatv.scan(event_loop, timeout=0)
    assert len(atvs) == 0


@pytest.mark.asyncio
async def test_zeroconf_scan_for_particular_device(event_loop):
    zeroconf_stub.stub(pyatv, HOMESHARING_SERVICE_1, HOMESHARING_SERVICE_2)

    atvs = await pyatv.scan(event_loop, timeout=0, identifier="BBBB")
    assert len(atvs) == 1
    assert atvs[0].name == "Apple TV 2"
    assert atvs[0].address == ipaddress.ip_address(IP_2)


@pytest.mark.asyncio
async def test_zeroconf_scan_device_info(event_loop):
    zeroconf_stub.stub(pyatv, MRP_SERVICE_1, AIRPLAY_SERVICE_2)

    atvs = await pyatv.scan(event_loop, timeout=0, protocol=Protocol.MRP)
    assert len(atvs) == 1

    device_info = atvs[0].device_info
    assert device_info.mac == AIRPLAY_ID


@pytest.mark.asyncio
async def test_udns_scan_no_results(udns_scan):
    atvs = await udns_scan()
    assert len(atvs) == 0


@pytest.mark.asyncio
async def test_udns_missing_port(udns_server, udns_scan):
    udns_server.add_service(fake_udns.mrp_service("dummy", "dummy", "dummy", port=None))

    atvs = await udns_scan()
    assert len(atvs) == 0


@pytest.mark.asyncio
async def test_udns_missing_properties(udns_server, udns_scan):
    udns_server.add_service(fake_udns.FakeDnsService("dummy", 1234, None))

    atvs = await udns_scan()
    assert len(atvs) == 0


@pytest.mark.asyncio
async def test_udns_scan_mrp(udns_server, udns_scan):
    udns_server.add_service(fake_udns.mrp_service("Apple TV", "Apple TV MRP", MRP_ID_1))

    atvs = await udns_scan()
    assert len(atvs) == 1

    assert_device(atvs[0], "Apple TV MRP", IP_LOCALHOST, MRP_ID_1, Protocol.MRP, 49152)


@pytest.mark.asyncio
async def test_udns_scan_airplay(udns_server, udns_scan):
    udns_server.add_service(fake_udns.airplay_service("Apple TV", AIRPLAY_ID))

    atvs = await udns_scan()
    assert len(atvs) == 0


@pytest.mark.asyncio
async def test_udns_scan_homesharing(udns_server, udns_scan):
    udns_server.add_service(fake_udns.homesharing_service("abcd", "Apple TV HS", HSGID))

    atvs = await udns_scan()
    assert len(atvs) == 1

    assert_device(
        atvs[0], "Apple TV HS", IP_LOCALHOST, "abcd", Protocol.DMAP, 3689, HSGID
    )


@pytest.mark.asyncio
async def test_scan_no_homesharing(udns_server, udns_scan):
    udns_server.add_service(fake_udns.device_service("Apple TV", "Apple TV Device"))

    atvs = await udns_scan()
    assert len(atvs) == 1

    assert_device(
        atvs[0], "Apple TV Device", IP_LOCALHOST, "Apple TV", Protocol.DMAP, 3689
    )


@pytest.mark.asyncio
async def test_scan_device_info(udns_server, udns_scan):
    udns_server.add_service(fake_udns.mrp_service("Apple TV", "Apple TV MRP", MRP_ID_1))
    udns_server.add_service(fake_udns.airplay_service("Apple TV", AIRPLAY_ID))

    atvs = await udns_scan()
    assert len(atvs) == 1

    device_info = atvs[0].device_info
    assert device_info.mac == AIRPLAY_ID
