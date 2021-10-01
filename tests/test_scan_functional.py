"""Functional tests for scanning.

The tests here are supposed to cover non-protocol specific aspects of
scanning, like scanning for a specific device or derive device model.
Two "generic" protocols (MRP and AirPlay) have been arbitrarily chosen
to have something to test with (could have been other protocols). They
are just called "service1" and "service2" to emphasize that the specific
protocols are irrelevant. Later, service3 was added as well...
"""

from ipaddress import ip_address

import pytest

from pyatv.const import DeviceModel, Protocol

from tests import fake_udns
from tests.conftest import Scanner
from tests.utils import assert_device

SERVICE_1_ID = "mrp_id_1"
SERVICE_1_NAME = "MRP ATV"
SERVICE_1_SERVICE_NAME = "MRP Service"
SERVICE_1_IP = "10.0.0.1"

SERVICE_2_ID = "AA:BB:CC:DD:EE:FF"
SERVICE_2_NAME = "AirPlay ATV"
SERVICE_2_IP = "10.0.0.2"

SERVICE_3_ID = "raopid"
SERVICE_3_NAME = "AirPlay ATV"

DEFAULT_KNOCK_PORTS = {3689, 7000, 49152, 32498}

pytestmark = pytest.mark.asyncio


def service1(model=None):
    return fake_udns.mrp_service(
        SERVICE_1_SERVICE_NAME,
        SERVICE_1_NAME,
        SERVICE_1_ID,
        addresses=[SERVICE_1_IP],
        model=model,
    )


def service2(address=SERVICE_1_IP):
    return fake_udns.airplay_service(SERVICE_2_NAME, SERVICE_2_ID, addresses=[address])


def service3():
    return fake_udns.raop_service(
        SERVICE_3_NAME, SERVICE_3_ID, addresses=[SERVICE_1_IP], port=5000
    )


def mrp_service_tvos_15():
    return fake_udns.mrp_service(
        SERVICE_1_SERVICE_NAME,
        SERVICE_1_NAME,
        SERVICE_1_ID,
        addresses=[SERVICE_1_IP],
        version="19J346",
    )


async def test_multicast_scan_no_device_found(multicast_scan: Scanner):
    atvs = await multicast_scan()
    assert len(atvs) == 0


async def test_multicast_scan_for_particular_device(udns_server, multicast_scan):
    udns_server.add_service(service1())
    udns_server.add_service(service2(address=SERVICE_1_IP))
    udns_server.add_service(service3())

    atvs = await multicast_scan(identifier={SERVICE_1_ID, SERVICE_2_ID})
    assert len(atvs) == 1

    assert atvs[0].name == SERVICE_2_NAME


async def test_multicast_scan_for_specific_devices(udns_server, multicast_scan):
    udns_server.add_service(service1())
    udns_server.add_service(service2(address=SERVICE_2_IP))

    atvs = await multicast_scan(identifier=SERVICE_2_ID)
    assert len(atvs) == 1
    assert atvs[0].name == SERVICE_2_NAME
    assert atvs[0].address == ip_address(SERVICE_2_IP)


async def test_multicast_scan_deep_sleeping_device(
    udns_server, multicast_scan: Scanner
):
    udns_server.sleep_proxy = True

    udns_server.add_service(service1())

    atvs = await multicast_scan()
    assert len(atvs) == 1
    assert atvs[0].deep_sleep


async def test_multicast_scan_device_info(udns_server, multicast_scan: Scanner):
    udns_server.add_service(service1())
    udns_server.add_service(service2())

    atvs = await multicast_scan()
    assert len(atvs) == 1

    device_info = atvs[0].device_info
    assert device_info.mac == SERVICE_2_ID


async def test_multicast_scan_device_model(udns_server, multicast_scan: Scanner):
    udns_server.add_service(service1(model="J105aAP"))

    atvs = await multicast_scan(protocol=Protocol.MRP)
    assert len(atvs) == 1

    device_info = atvs[0].device_info
    assert device_info.model == DeviceModel.Gen4K


async def test_multicast_filter_multiple_protocols(
    udns_server, multicast_scan: Scanner
):
    udns_server.add_service(service1())
    udns_server.add_service(service2())
    udns_server.add_service(service3())

    atvs = await multicast_scan(protocol={Protocol.MRP, Protocol.RAOP})
    assert len(atvs) == 1

    atv = atvs[0]
    assert len(atv.services) == 2
    assert atv.get_service(Protocol.MRP) is not None
    assert atv.get_service(Protocol.RAOP) is not None


async def test_multicast_ignore_mrp_tvos15(udns_server, multicast_scan: Scanner):
    udns_server.add_service(mrp_service_tvos_15())

    atvs = await multicast_scan()
    assert len(atvs) == 0


async def test_unicast_scan_no_results(unicast_scan: Scanner):
    atvs = await unicast_scan()
    assert len(atvs) == 0


async def test_unicast_missing_port(udns_server, unicast_scan: Scanner):
    udns_server.add_service(
        fake_udns.FakeDnsService("dummy", SERVICE_1_IP, None, None, None)
    )

    atvs = await unicast_scan()
    assert len(atvs) == 0


async def test_unicast_missing_properties(udns_server, unicast_scan: Scanner):
    udns_server.add_service(
        fake_udns.FakeDnsService("dummy", SERVICE_1_IP, 1234, None, None)
    )

    atvs = await unicast_scan()
    assert len(atvs) == 0


async def test_unicast_scan_device_info(udns_server, unicast_scan: Scanner):
    udns_server.add_service(service1())
    udns_server.add_service(service2())

    atvs = await unicast_scan()
    assert len(atvs) == 1

    device_info = atvs[0].device_info
    assert device_info.mac == SERVICE_2_ID


async def test_unicast_scan_device_model(udns_server, unicast_scan: Scanner):
    udns_server.add_service(service1(model="J105aAP"))

    atvs = await unicast_scan()
    assert len(atvs) == 1

    device_info = atvs[0].device_info
    assert device_info.model == DeviceModel.Gen4K


async def test_unicast_scan_port_knock(unicast_scan: Scanner, stub_knock_server):
    await unicast_scan()
    assert stub_knock_server.ports == DEFAULT_KNOCK_PORTS
    assert stub_knock_server.knock_count == 1


async def test_unicast_filter_multiple_protocols(udns_server, unicast_scan: Scanner):
    udns_server.add_service(service1())
    udns_server.add_service(service2())
    udns_server.add_service(service3())

    atvs = await unicast_scan(protocol={Protocol.MRP, Protocol.RAOP})
    assert len(atvs) == 1

    atv = atvs[0]
    assert len(atv.services) == 2
    assert atv.get_service(Protocol.MRP) is not None
    assert atv.get_service(Protocol.RAOP) is not None


async def test_unicast_ignore_mrp_tvos15(udns_server, unicast_scan: Scanner):
    udns_server.add_service(mrp_service_tvos_15())

    atvs = await unicast_scan()
    assert len(atvs) == 0
