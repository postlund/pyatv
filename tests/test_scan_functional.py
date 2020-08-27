"""Scanning tests with fake mDNS responder.."""

import pyatv
from ipaddress import ip_address

from unittest.mock import patch

import pytest

from pyatv.const import Protocol, DeviceModel
from tests import fake_udns


IP_1 = "10.0.0.1"
IP_2 = "10.0.0.2"
IP_3 = "10.0.0.3"
IP_LOCALHOST = "127.0.0.1"

HSGID = "hsgid"

MRP_ID_1 = "mrp_id_1"

AIRPLAY_ID = "AA:BB:CC:DD:EE:FF"

DEFAULT_KNOCK_PORTS = {3689, 7000, 49152, 32498}


def _get_atv(atvs, ip):
    for atv in atvs:
        if atv.address == ip_address(ip):
            return atv
    return None


def assert_device(atv, name, address, identifier, protocol, port, creds=None):
    assert atv.name == name
    assert atv.address == address
    assert atv.identifier == identifier
    assert atv.get_service(protocol)
    assert atv.get_service(protocol).port == port
    assert atv.get_service(protocol).credentials == creds


# stub_knock_server is added here to make sure all UDNS tests uses a stubbed
# knock server
@pytest.fixture
async def udns_server(event_loop, stub_knock_server):
    server = fake_udns.FakeUdns(event_loop)
    await server.start()
    yield server
    server.close()


@pytest.fixture
async def multicast_scan(event_loop, udns_server):
    async def _scan(timeout=1, identifier=None, protocol=None):
        with fake_udns.stub_multicast(udns_server, event_loop):
            return await pyatv.scan(
                event_loop, identifier=identifier, protocol=protocol, timeout=timeout
            )

    yield _scan


@pytest.fixture
async def unicast_scan(event_loop, udns_server):
    async def _scan(timeout=1):
        port = str(udns_server.port)
        with patch.dict("os.environ", {"PYATV_UDNS_PORT": port}):
            return await pyatv.scan(event_loop, hosts=[IP_LOCALHOST], timeout=timeout)

    yield _scan


@pytest.mark.asyncio
async def test_multicast_scan_no_device_found(multicast_scan):
    atvs = await multicast_scan()
    assert len(atvs) == 0


@pytest.mark.asyncio
async def test_multicast_scan(udns_server, multicast_scan):
    udns_server.add_service(
        fake_udns.mrp_service("Apple TV", "Apple TV MRP", MRP_ID_1, address=IP_1)
    )
    udns_server.add_service(
        fake_udns.homesharing_service("abcd", "Apple TV HS 2", HSGID, address=IP_2)
    )
    udns_server.add_service(
        fake_udns.device_service("efgh", "Apple TV Device", address=IP_3)
    )

    atvs = await multicast_scan()
    assert len(atvs) == 3

    # First device
    dev1 = _get_atv(atvs, IP_1)
    assert dev1
    assert dev1.identifier == MRP_ID_1

    # Second device
    dev2 = _get_atv(atvs, IP_2)
    assert dev2
    assert dev2.identifier == "abcd"

    # Third device
    dev3 = _get_atv(atvs, IP_3)
    assert dev3
    assert dev3.identifier == "efgh"


@pytest.mark.asyncio
async def test_multicast_scan_no_home_sharing(udns_server, multicast_scan):
    udns_server.add_service(
        fake_udns.device_service("efgh", "Apple TV Device", address=IP_3)
    )

    atvs = await multicast_scan()
    assert len(atvs) == 1

    assert_device(
        atvs[0], "Apple TV Device", ip_address(IP_3), "efgh", Protocol.DMAP, 3689
    )


@pytest.mark.asyncio
async def test_multicast_scan_home_sharing_merge(udns_server, multicast_scan):
    udns_server.add_service(
        fake_udns.device_service("efgh", "Apple TV Device", address=IP_3)
    )
    udns_server.add_service(
        fake_udns.homesharing_service("efgh", "Apple TV Device", HSGID, address=IP_3)
    )

    atvs = await multicast_scan()
    assert len(atvs) == 1

    assert_device(
        atvs[0], "Apple TV Device", ip_address(IP_3), "efgh", Protocol.DMAP, 3689, HSGID
    )


@pytest.mark.asyncio
async def test_multicast_scan_mrp(udns_server, multicast_scan):
    udns_server.add_service(
        fake_udns.mrp_service("Apple TV 1", "Apple TV MRP 1", MRP_ID_1, address=IP_1)
    )
    udns_server.add_service(
        fake_udns.device_service("efgh", "Apple TV Device", address=IP_3)
    )

    atvs = await multicast_scan(protocol=Protocol.MRP)
    assert len(atvs) == 1

    dev1 = _get_atv(atvs, IP_1)
    assert dev1
    assert dev1.name == "Apple TV MRP 1"
    assert dev1.get_service(Protocol.MRP)


@pytest.mark.asyncio
async def test_multicast_scan_airplay_device(udns_server, multicast_scan):
    udns_server.add_service(
        fake_udns.airplay_service("Apple TV", AIRPLAY_ID, address=IP_1)
    )

    atvs = await multicast_scan()
    assert len(atvs) == 0


@pytest.mark.asyncio
async def test_multicast_scan_for_particular_device(udns_server, multicast_scan):
    udns_server.add_service(
        fake_udns.mrp_service("Apple TV 1", "Apple TV MRP 1", MRP_ID_1, address=IP_1)
    )
    udns_server.add_service(
        fake_udns.homesharing_service("efgh", "Apple TV Device", HSGID, address=IP_3)
    )

    atvs = await multicast_scan(identifier="efgh")
    assert len(atvs) == 1
    assert atvs[0].name == "Apple TV Device"
    assert atvs[0].address == ip_address(IP_3)


@pytest.mark.asyncio
async def test_multicast_scan_deep_sleeping_device(udns_server, multicast_scan):
    udns_server.sleep_proxy = True

    udns_server.add_service(
        fake_udns.mrp_service("Apple TV 1", "Apple TV MRP 1", MRP_ID_1, address=IP_1)
    )

    atvs = await multicast_scan()
    assert len(atvs) == 1
    assert atvs[0].deep_sleep


@pytest.mark.asyncio
async def test_multicast_scan_device_info(udns_server, multicast_scan):
    udns_server.add_service(
        fake_udns.mrp_service("Apple TV 1", "Apple TV MRP 1", MRP_ID_1, address=IP_1)
    )
    udns_server.add_service(
        fake_udns.airplay_service("Apple TV", AIRPLAY_ID, address=IP_1)
    )

    atvs = await multicast_scan(protocol=Protocol.MRP)
    assert len(atvs) == 1

    device_info = atvs[0].device_info
    assert device_info.mac == AIRPLAY_ID


@pytest.mark.asyncio
async def test_multicast_scan_device_model(udns_server, multicast_scan):
    udns_server.add_service(
        fake_udns.mrp_service(
            "Apple TV 1", "Apple TV MRP 1", MRP_ID_1, address=IP_1, model="J105aAP"
        )
    )

    atvs = await multicast_scan(protocol=Protocol.MRP)
    assert len(atvs) == 1

    device_info = atvs[0].device_info
    assert device_info.model == DeviceModel.Gen4K


@pytest.mark.asyncio
async def test_unicast_scan_no_results(unicast_scan):
    atvs = await unicast_scan()
    assert len(atvs) == 0


@pytest.mark.asyncio
async def test_unicast_missing_port(udns_server, unicast_scan):
    udns_server.add_service(fake_udns.mrp_service("dummy", "dummy", "dummy", port=None))

    atvs = await unicast_scan()
    assert len(atvs) == 0


@pytest.mark.asyncio
async def test_unicast_missing_properties(udns_server, unicast_scan):
    udns_server.add_service(fake_udns.FakeDnsService("dummy", IP_1, 1234, None, None))

    atvs = await unicast_scan()
    assert len(atvs) == 0


@pytest.mark.asyncio
async def test_unicast_scan_mrp(udns_server, unicast_scan):
    udns_server.add_service(fake_udns.mrp_service("Apple TV", "Apple TV MRP", MRP_ID_1))

    atvs = await unicast_scan()
    assert len(atvs) == 1

    assert_device(
        atvs[0], "Apple TV MRP", ip_address(IP_LOCALHOST), MRP_ID_1, Protocol.MRP, 49152
    )


@pytest.mark.asyncio
async def test_unicast_scan_airplay(udns_server, unicast_scan):
    udns_server.add_service(
        fake_udns.airplay_service("Apple TV", AIRPLAY_ID, address=IP_1)
    )

    atvs = await unicast_scan()
    assert len(atvs) == 0


@pytest.mark.asyncio
async def test_unicast_scan_homesharing(udns_server, unicast_scan):
    udns_server.add_service(
        fake_udns.homesharing_service("abcd", "Apple TV HS", HSGID, address=IP_3)
    )

    atvs = await unicast_scan()
    assert len(atvs) == 1

    assert_device(
        atvs[0],
        "Apple TV HS",
        ip_address(IP_3),
        "abcd",
        Protocol.DMAP,
        3689,
        HSGID,
    )


@pytest.mark.asyncio
async def test_unicast_scan_no_homesharing(udns_server, unicast_scan):
    udns_server.add_service(
        fake_udns.device_service("Apple TV", "Apple TV Device", address=IP_2)
    )

    atvs = await unicast_scan()
    assert len(atvs) == 1

    assert_device(
        atvs[0],
        "Apple TV Device",
        ip_address(IP_2),
        "Apple TV",
        Protocol.DMAP,
        3689,
    )


@pytest.mark.asyncio
async def test_unicast_scan_device_info(udns_server, unicast_scan):
    udns_server.add_service(
        fake_udns.mrp_service("Apple TV", "Apple TV MRP", MRP_ID_1, address=IP_1)
    )
    udns_server.add_service(
        fake_udns.airplay_service("Apple TV", AIRPLAY_ID, address=IP_1)
    )

    atvs = await unicast_scan()
    assert len(atvs) == 1

    device_info = atvs[0].device_info
    assert device_info.mac == AIRPLAY_ID


@pytest.mark.asyncio
async def test_unicast_scan_device_model(udns_server, unicast_scan):
    udns_server.add_service(
        fake_udns.mrp_service(
            "Apple TV 1", "Apple TV MRP 1", MRP_ID_1, address=IP_1, model="J105aAP"
        )
    )

    atvs = await unicast_scan()
    assert len(atvs) == 1

    device_info = atvs[0].device_info
    assert device_info.model == DeviceModel.Gen4K


@pytest.mark.asyncio
async def test_unicast_scan_port_knock(unicast_scan, stub_knock_server):
    await unicast_scan()
    assert stub_knock_server.ports == DEFAULT_KNOCK_PORTS
    assert stub_knock_server.knock_count == 1
