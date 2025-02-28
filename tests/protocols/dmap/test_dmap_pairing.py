"""Test suit for pairing process with Apple TV."""

import asyncio
import ipaddress
from unittest.mock import MagicMock

import pytest
import pytest_asyncio

from pyatv.conf import AppleTV, ManualService
from pyatv.const import Protocol
from pyatv.core import create_core
from pyatv.protocols.dmap import pairing, parser, tag_definitions
from pyatv.storage.memory_storage import MemoryStorage

from tests import utils, zeroconf_stub

REMOTE_NAME = "pyatv remote"

# This is a valid config for default pairing guid
PIN_CODE = 1234
PAIRING_GUID = "0x0000000000000001"
PAIRING_CODE = "690E6FF61E0D7C747654A42AED17047D"

# This is valid for a some other (non-default) config
PIN_CODE2 = 5555
PAIRING_GUID2 = "0x1234ABCDE56789FF"
PAIRING_CODE2 = "58AD1D195B6DAA58AA2EA29DC25B81C3"

# Code is padded with zeros
PIN_CODE3 = 1
PAIRING_GUID3 = "0x7D1324235F535AE7"
PAIRING_CODE3 = "A34C3361C7D57D61CA41F62A8042F069"

# Pairing guid is 8 bytes, which is 64 bits
RANDOM_128_BITS = 6558272190156386627
RANDOM_PAIRING_GUID = "0x5B03A9CF4A983143"
RANDOM_PAIRING_CODE = "7AF2D0B8629DE3C704D40A14C9E8CB93"

pytestmark = pytest.mark.asyncio


def pairing_url(zeroconf, pairing_code):
    service = zeroconf.registered_services[0]
    return (
        f"http://127.0.0.1:{service.port}/"
        + f"pair?pairingcode={pairing_code}&servicename=test"
    )


@pytest.fixture
def mock_random():
    pairing.random.getrandbits = lambda x: RANDOM_128_BITS


@pytest.fixture(name="storage")
def storage_fixture() -> MemoryStorage:
    yield MemoryStorage()


@pytest_asyncio.fixture
async def mock_pairing(storage):
    obj = MagicMock()

    service = ManualService("id", Protocol.DMAP, 0, {})
    config = AppleTV("Apple TV", "127.0.0.1")
    config.add_service(service)
    zeroconf = zeroconf_stub.stub(pairing)

    async def _start(
        pin_code=PIN_CODE, pairing_guid=PAIRING_GUID, name=REMOTE_NAME, addresses=None
    ):
        options = {"zeroconf": zeroconf}
        if pairing_guid:
            options["pairing_guid"] = pairing_guid
        if name:
            options["name"] = name
        if addresses:
            options["addresses"] = addresses

        settings = await storage.get_settings(config)
        core = await create_core(
            config, service, settings=settings, loop=asyncio.get_running_loop()
        )

        obj.pairing = pairing.DmapPairingHandler(core, **options)
        await obj.pairing.begin()
        obj.pairing.pin(pin_code)
        return obj.pairing, zeroconf, service

    yield _start
    await obj.pairing.finish()
    await obj.pairing.close()


async def test_zeroconf_service_published(mock_pairing):
    _, zeroconf, _ = await mock_pairing()

    assert len(zeroconf.registered_services) == 1, "no zeroconf service registered"

    service = zeroconf.registered_services[0]
    assert service.properties[b"DvNm"] == REMOTE_NAME.encode(
        "utf-8"
    ), "remote name does not match"
    assert [ipaddress.ip_address("10.0.10.1").packed] == service.addresses


@pytest.mark.parametrize("addresses", [["1.2.3.4"]])
async def test_zeroconf_custom_addresses(mock_pairing, addresses):
    _, zeroconf, _ = await mock_pairing(addresses=addresses)

    assert len(zeroconf.registered_services) == len(addresses)

    service = zeroconf.registered_services[0]
    for address in addresses:
        assert ipaddress.ip_address(address).packed in service.addresses


async def test_succesful_pairing(mock_pairing, storage):
    pairing, zeroconf, service = await mock_pairing()

    url = pairing_url(zeroconf, PAIRING_CODE)
    data, _ = await utils.simple_get(url)

    await pairing.finish()

    # Verify content returned in pairingresponse
    parsed = parser.parse(data, tag_definitions.lookup_tag)
    assert parser.first(parsed, "cmpa", "cmpg") == 1
    assert parser.first(parsed, "cmpa", "cmnm") == REMOTE_NAME
    assert parser.first(parsed, "cmpa", "cmty") == "iPhone"

    assert service.credentials == PAIRING_GUID
    assert storage.settings[0].protocols.dmap.credentials == PAIRING_GUID


async def test_successful_pairing_random_pairing_guid_generated(
    mock_random, mock_pairing, storage
):
    pairing, zeroconf, service = await mock_pairing(pairing_guid=None)

    url = pairing_url(zeroconf, RANDOM_PAIRING_CODE)
    await utils.simple_get(url)

    await pairing.finish()

    assert service.credentials == RANDOM_PAIRING_GUID
    assert storage.settings[0].protocols.dmap.credentials == RANDOM_PAIRING_GUID


async def test_succesful_pairing_with_any_pin(mock_pairing):
    _, zeroconf, _ = await mock_pairing(pin_code=None)

    url = pairing_url(zeroconf, "invalid_pairing_code")
    _, status = await utils.simple_get(url)

    assert status == 200


async def test_succesful_pairing_with_pin_leadering_zeros(mock_pairing):
    _, zeroconf, _ = await mock_pairing(pin_code=PIN_CODE3, pairing_guid=PAIRING_GUID3)

    url = pairing_url(zeroconf, PAIRING_CODE3)
    _, status = await utils.simple_get(url)

    assert status == 200


async def test_pair_custom_pairing_guid(mock_pairing, storage):
    pairing, zeroconf, service = await mock_pairing(
        pin_code=PIN_CODE2, pairing_guid=PAIRING_GUID2
    )

    url = pairing_url(zeroconf, PAIRING_CODE2)
    data, _ = await utils.simple_get(url)

    await pairing.finish()

    # Verify content returned in pairingresponse
    parsed = parser.parse(data, tag_definitions.lookup_tag)
    assert parser.first(parsed, "cmpa", "cmpg") == int(PAIRING_GUID2, 16)

    assert service.credentials == PAIRING_GUID2
    assert storage.settings[0].protocols.dmap.credentials == PAIRING_GUID2


async def test_failed_pairing(mock_pairing):
    _, zeroconf, _ = await mock_pairing()

    url = pairing_url(zeroconf, "wrong")
    data, status = await utils.simple_get(url)

    assert status == 500
