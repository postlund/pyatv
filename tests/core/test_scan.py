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
from pyatv.core.scan import get_unique_identifiers

TEST_SERVICE1 = Service("_service1._tcp.local", "service1", None, 0, {"a": "b"})
TEST_SERVICE2 = Service("_service2._tcp.local", "service2", None, 0, {"c": "d"})

ALL_MDNS_SERVICES = [
    "_mediaremotetv._tcp.local.",
    "_companion-link._tcp.local.",
    "_airport._tcp.local.",
    "_sleep-proxy._udp.local.",
    "_touch-able._tcp.local.",
    "_appletv-v2._tcp.local.",
    "_hscp._tcp.local.",
    "_airplay._tcp.local.",
    "_raop._tcp.local.",
]

DEVICE_A_RECORD = DNSAddress(
    "Ohana.local.",
    const._TYPE_A,
    const._CLASS_IN,
    const._DNS_HOST_TTL,
    b"\xc0\xa8k\xb8",
)
SLEEP_PROXY_PTR_RECORD = DNSPointer(
    "_sleep-proxy._udp.local.",
    const._TYPE_PTR,
    const._CLASS_IN,
    const._DNS_OTHER_TTL,
    "70-35-60-63.1 Ohana._sleep-proxy._udp.local.",
)
SLEEP_PROXY_SRV_RECORD = DNSService(
    "70-35-60-63.1 Ohana._sleep-proxy._udp.local.",
    const._TYPE_SRV,
    const._CLASS_IN,
    const._DNS_HOST_TTL,
    0,
    0,
    54942,
    "Ohana.local.",
)
SLEEP_PROXY_TXT_RECORD = DNSText(
    "70-35-60-63.1 Ohana._sleep-proxy._udp.local.",
    const._TYPE_TXT,
    const._CLASS_IN,
    const._DNS_OTHER_TTL,
    b"",
)
AIRPLAY_PTR_RECORD = DNSPointer(
    "_airplay._tcp.local.",
    const._TYPE_PTR,
    const._CLASS_IN,
    const._DNS_OTHER_TTL,
    "Ohana._airplay._tcp.local.",
)
AIRPLAY_SRV_RECORD = DNSService(
    "Ohana._airplay._tcp.local.",
    const._TYPE_SRV,
    const._CLASS_IN,
    const._DNS_HOST_TTL,
    0,
    0,
    7000,
    "Ohana.local.",
)
AIRPLAY_TXT_RECORD = DNSText(
    "Ohana._airplay._tcp.local.",
    const._TYPE_TXT,
    const._CLASS_IN,
    const._DNS_OTHER_TTL,
    b"",
)
RAOP_PTR_RECORD = DNSPointer(
    "_raop._tcp.local.",
    const._TYPE_PTR,
    const._CLASS_IN,
    const._DNS_OTHER_TTL,
    "54E61BF2ED74@Ohana._raop._tcp.local.",
)
RAOP_SERVICE_RECORD = DNSService(
    "54E61BF2ED74@Ohana._raop._tcp.local.",
    const._TYPE_SRV,
    const._CLASS_IN,
    const._DNS_HOST_TTL,
    0,
    0,
    7000,
    "Ohana.local.",
)
RAOP_TXT_RECORD = DNSText(
    "Ohana._airplay._tcp.local.",
    const._TYPE_TXT,
    const._CLASS_IN,
    const._DNS_OTHER_TTL,
    b"",
)
COMPANION_LINK_PTR_RECORD = DNSPointer(
    "_companion-link._tcp.local.",
    const._TYPE_PTR,
    const._CLASS_IN,
    const._DNS_OTHER_TTL,
    "Ohana._companion-link._tcp.local.",
)
COMPANION_LINK_SRV_RECORD = DNSService(
    "Ohana._companion-link._tcp.local.",
    const._TYPE_SRV,
    const._CLASS_IN,
    const._DNS_HOST_TTL,
    0,
    0,
    49152,
    "Ohana.local.",
)
COMPANION_LINK_TXT_RECORD = DNSText(
    "Ohana._companion-link._tcp.local.",
    const._TYPE_TXT,
    const._CLASS_IN,
    const._DNS_OTHER_TTL,
    b"",
)
DEVICE_INFO_TEXT_RECORD = DNSText(
    "Ohana._device-info._tcp.local.",
    const._TYPE_TXT,
    const._CLASS_IN,
    const._DNS_OTHER_TTL,
    b"\x0Cmodel=J305AP",
)
SLEEP_PROXY_RECORDS = [
    SLEEP_PROXY_PTR_RECORD,
    SLEEP_PROXY_SRV_RECORD,
    SLEEP_PROXY_TXT_RECORD,
]
AIRPLAY_RECORDS = [
    AIRPLAY_PTR_RECORD,
    AIRPLAY_SRV_RECORD,
    AIRPLAY_TXT_RECORD,
]
RAOP_RECORDS = [
    RAOP_PTR_RECORD,
    RAOP_SERVICE_RECORD,
    RAOP_TXT_RECORD,
]
COMPANION_LINK_RECORDS = [
    COMPANION_LINK_PTR_RECORD,
    COMPANION_LINK_SRV_RECORD,
    COMPANION_LINK_TXT_RECORD,
]


COMPLETE_RECORD_SET_WITH_DEVICE_INFO = [
    DEVICE_A_RECORD,
    *SLEEP_PROXY_RECORDS,
    *AIRPLAY_RECORDS,
    *RAOP_RECORDS,
    *COMPANION_LINK_RECORDS,
    DEVICE_INFO_TEXT_RECORD,
]
COMPLETE_RECORD_SET = [
    DEVICE_A_RECORD,
    *SLEEP_PROXY_RECORDS,
    *AIRPLAY_RECORDS,
    *RAOP_RECORDS,
    *COMPANION_LINK_RECORDS,
]
RECORD_SET_WITH_DEVICE_INFO_MISSING_COMPANION_LINK = [
    DEVICE_A_RECORD,
    *SLEEP_PROXY_RECORDS,
    *AIRPLAY_RECORDS,
    *RAOP_RECORDS,
    DEVICE_INFO_TEXT_RECORD,
]
PARTIAL_RECORD_SET = [
    DEVICE_A_RECORD,
    *SLEEP_PROXY_RECORDS,
    *AIRPLAY_RECORDS,
]


from typing import List, Tuple

from zeroconf import DNSRecord


async def _create_zc_with_cache(
    records: List[DNSRecord],
) -> Tuple[AsyncZeroconf, AsyncServiceBrowser]:
    aiozc = AsyncZeroconf(interfaces=["127.0.0.1"])
    browser = AsyncServiceBrowser(
        aiozc.zeroconf,
        ALL_MDNS_SERVICES,
        None,
        DummyListener(),
    )
    aiozc.zeroconf.cache.async_add_records(records)
    await aiozc.zeroconf.async_wait_for_start()
    return aiozc, browser


@pytest.fixture
def response():
    yield Response([], False, None)


class DummyListener(ServiceListener):
    def add_service(self, zeroconf: Zeroconf, type: str, name: str) -> None:
        pass

    def remove_service(self, zeroconf: Zeroconf, type: str, name: str) -> None:
        pass

    def update_service(self, zeroconf: Zeroconf, type: str, name: str) -> None:
        pass


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
async def test_scan_with_zeroconf_complete_and_device_info():
    aiozc, browser = await _create_zc_with_cache(COMPLETE_RECORD_SET_WITH_DEVICE_INFO)
    results = await scan(asyncio.get_event_loop(), timeout=0, aiozc=aiozc)
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


@pytest.mark.asyncio
async def test_scan_with_zeroconf_complete_and_device_info_specific_host_matching():
    aiozc, browser = await _create_zc_with_cache(COMPLETE_RECORD_SET_WITH_DEVICE_INFO)
    results = await scan(
        asyncio.get_event_loop(),
        hosts=["192.168.107.184"],
        timeout=0,
        aiozc=aiozc,
    )
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


@pytest.mark.asyncio
async def test_scan_with_zeroconf_complete_and_device_info_specific_host_not_matching():
    aiozc, browser = await _create_zc_with_cache(COMPLETE_RECORD_SET_WITH_DEVICE_INFO)
    results = await scan(
        asyncio.get_event_loop(), hosts=["192.168.1.1"], timeout=0, aiozc=aiozc
    )
    assert len(results) == 0
    await browser.async_cancel()
    await aiozc.async_close()


@pytest.mark.asyncio
async def test_scan_with_zeroconf_complete():
    aiozc, browser = await _create_zc_with_cache(COMPLETE_RECORD_SET)
    results = await scan(asyncio.get_event_loop(), timeout=0, aiozc=aiozc)
    atv: AppleTV = results[0]
    assert isinstance(atv, AppleTV)
    assert "_sleep-proxy._udp.local" in atv.properties
    assert "_airplay._tcp.local" in atv.properties
    assert "_raop._tcp.local" in atv.properties
    assert "_companion-link._tcp.local" in atv.properties
    assert atv.deep_sleep is False
    assert atv.device_info.model == DeviceModel.Unknown
    await browser.async_cancel()
    await aiozc.async_close()


@pytest.mark.asyncio
async def test_scan_with_zeroconf_partial():
    aiozc, browser = await _create_zc_with_cache(PARTIAL_RECORD_SET)
    results = await scan(asyncio.get_event_loop(), timeout=0, aiozc=aiozc)
    assert len(results) == 0
    await browser.async_cancel()
    await aiozc.async_close()


@pytest.mark.asyncio
async def test_scan_with_zeroconf_missing_companion_link_only():
    aiozc, browser = await _create_zc_with_cache(
        RECORD_SET_WITH_DEVICE_INFO_MISSING_COMPANION_LINK
    )
    results = await scan(asyncio.get_event_loop(), timeout=0, aiozc=aiozc)
    atv: AppleTV = results[0]
    assert isinstance(atv, AppleTV)
    assert "_sleep-proxy._udp.local" in atv.properties
    assert "_airplay._tcp.local" in atv.properties
    assert "_raop._tcp.local" in atv.properties
    assert "_companion-link._tcp.local" not in atv.properties
    assert atv.deep_sleep is False
    assert atv.device_info.model == DeviceModel.AppleTV4KGen2
    await browser.async_cancel()
    await aiozc.async_close()
