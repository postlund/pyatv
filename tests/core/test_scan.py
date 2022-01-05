"""Unit tests for scan module."""

import asyncio
from unittest.mock import patch

import pytest
from zeroconf import (
    DNSAddress,
    DNSPointer,
    DNSService,
    DNSText,
    ServiceListener,
    Zeroconf,
    const,
)
from zeroconf.asyncio import AsyncServiceBrowser, AsyncZeroconf

from pyatv import scan
from pyatv.conf import AppleTV
from pyatv.const import DeviceModel
from pyatv.core.mdns import Response, Service
from pyatv.core.scan import BaseScanner, get_unique_identifiers

TEST_SERVICE1 = Service("_service1._tcp.local", "service1", None, 0, {"a": "b"})
TEST_SERVICE2 = Service("_service2._tcp.local", "service2", None, 0, {"c": "d"})


@pytest.fixture
def response():
    yield Response([], False, None)


def test_unique_identifier_empty(response):
    assert len(list(get_unique_identifiers(response))) == 0


@patch("pyatv.core.scan.get_unique_id")
def test_unique_identifiers(unique_id_mock, response):
    response.services.append(TEST_SERVICE1)
    response.services.append(TEST_SERVICE2)

    unique_id_mock.side_effect = ["id1", "id2"]

    identifiers = get_unique_identifiers(response)

    assert "id1" == next(identifiers)
    unique_id_mock.assert_called_with("_service1._tcp.local", "service1", {"a": "b"})
    assert "id2" == next(identifiers)
    unique_id_mock.assert_called_with("_service2._tcp.local", "service2", {"c": "d"})
    assert not next(identifiers, None)


@pytest.mark.asyncio
async def test_scan_with_zeroconf():
    if not hasattr(asyncio, "get_running_loop"):
        # until python 3.6 is removed, its EOL anyways
        asyncio.get_running_loop = asyncio.get_event_loop
    aiozc = AsyncZeroconf(interfaces=["127.0.0.1"])

    class DummyListener(ServiceListener):
        def add_service(self, zeroconf: Zeroconf, type: str, name: str) -> None:
            pass

        def remove_service(self, zeroconf: Zeroconf, type: str, name: str) -> None:
            pass

        def update_service(self, zeroconf: Zeroconf, type: str, name: str) -> None:
            pass

    browser = AsyncServiceBrowser(
        aiozc.zeroconf,
        [
            "_mediaremotetv._tcp.local.",
            "_companion-link._tcp.local.",
            "_airport._tcp.local.",
            "_sleep-proxy._udp.local.",
            "_touch-able._tcp.local.",
            "_appletv-v2._tcp.local.",
            "_hscp._tcp.local.",
            "_airplay._tcp.local.",
            "_raop._tcp.local.",
        ],
        None,
        DummyListener(),
    )
    a_record = DNSAddress(
        "Ohana.local.",
        const._TYPE_A,
        const._CLASS_IN,
        const._DNS_HOST_TTL,
        b"\xc0\xa8k\xb8",
    )

    sleep_proxy_ptr_record = DNSPointer(
        "_sleep-proxy._udp.local.",
        const._TYPE_PTR,
        const._CLASS_IN,
        const._DNS_OTHER_TTL,
        "70-35-60-63.1 Ohana._sleep-proxy._udp.local.",
    )
    sleep_proxy_service_record = DNSService(
        "70-35-60-63.1 Ohana._sleep-proxy._udp.local.",
        const._TYPE_SRV,
        const._CLASS_IN,
        const._DNS_HOST_TTL,
        0,
        0,
        54942,
        "Ohana.local.",
    )
    sleep_proxy_txt_record = DNSText(
        "70-35-60-63.1 Ohana._sleep-proxy._udp.local.",
        const._TYPE_TXT,
        const._CLASS_IN,
        const._DNS_OTHER_TTL,
        b"",
    )

    airplay_ptr_record = DNSPointer(
        "_airplay._tcp.local.",
        const._TYPE_PTR,
        const._CLASS_IN,
        const._DNS_OTHER_TTL,
        "Ohana._airplay._tcp.local.",
    )
    airplay_service_record = DNSService(
        "Ohana._airplay._tcp.local.",
        const._TYPE_SRV,
        const._CLASS_IN,
        const._DNS_HOST_TTL,
        0,
        0,
        7000,
        "Ohana.local.",
    )
    airplay_txt_record = DNSText(
        "Ohana._airplay._tcp.local.",
        const._TYPE_TXT,
        const._CLASS_IN,
        const._DNS_OTHER_TTL,
        b"",
    )

    raop_ptr_record = DNSPointer(
        "_raop._tcp.local.",
        const._TYPE_PTR,
        const._CLASS_IN,
        const._DNS_OTHER_TTL,
        "54E61BF2ED74@Ohana._raop._tcp.local.",
    )
    raop_service_record = DNSService(
        "54E61BF2ED74@Ohana._raop._tcp.local.",
        const._TYPE_SRV,
        const._CLASS_IN,
        const._DNS_HOST_TTL,
        0,
        0,
        7000,
        "Ohana.local.",
    )
    raop_txt_record = DNSText(
        "Ohana._airplay._tcp.local.",
        const._TYPE_TXT,
        const._CLASS_IN,
        const._DNS_OTHER_TTL,
        b"",
    )

    companion_link_ptr_record = DNSPointer(
        "_companion-link._tcp.local.",
        const._TYPE_PTR,
        const._CLASS_IN,
        const._DNS_OTHER_TTL,
        "Ohana._companion-link._tcp.local.",
    )
    companion_link_service_record = DNSService(
        "Ohana._companion-link._tcp.local.",
        const._TYPE_SRV,
        const._CLASS_IN,
        const._DNS_HOST_TTL,
        0,
        0,
        49152,
        "Ohana.local.",
    )
    companion_link_txt_record = DNSText(
        "Ohana._companion-link._tcp.local.",
        const._TYPE_TXT,
        const._CLASS_IN,
        const._DNS_OTHER_TTL,
        b"",
    )
    device_info_ptr_record = DNSPointer(
        "_device-info._tcp.local.",
        const._TYPE_PTR,
        const._CLASS_IN,
        const._DNS_OTHER_TTL,
        "Ohana._device-info._tcp.local.",
    )
    device_info_txt_record = DNSText(
        "Ohana._device-info._tcp.local.",
        const._TYPE_TXT,
        const._CLASS_IN,
        const._DNS_OTHER_TTL,
        b"\x0Cmodel=J305AP",
    )

    aiozc.zeroconf.cache.async_add_records(
        [
            a_record,
            sleep_proxy_ptr_record,
            sleep_proxy_service_record,
            sleep_proxy_txt_record,
            airplay_ptr_record,
            airplay_service_record,
            airplay_txt_record,
            raop_ptr_record,
            raop_service_record,
            raop_txt_record,
            companion_link_ptr_record,
            companion_link_service_record,
            companion_link_txt_record,
            device_info_ptr_record,
            device_info_txt_record,
        ]
    )
    await aiozc.zeroconf.async_wait_for_start()
    results = await scan(asyncio.get_event_loop(), timeout=0.1, async_zeroconf=aiozc)
    atv: AppleTV = results[0]
    assert isinstance(atv, AppleTV)
    assert "_sleep-proxy._udp.local" in atv.properties
    assert "_airplay._tcp.local" in atv.properties
    assert "_raop._tcp.local" in atv.properties
    assert "_companion-link._tcp.local" in atv.properties
    assert atv.deep_sleep is False
    assert atv.device_info.model == DeviceModel.AppleTV4KGen2
    await browser.async_cancel()
    await aiozc.async_close()
