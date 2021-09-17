"""Test suit for pairing process with Apple TV."""

import ipaddress
from unittest.mock import MagicMock

import pytest

from pyatv.conf import AppleTV, ManualService
from pyatv.const import Protocol
from pyatv.protocols.dmap import pairing, parser, tag_definitions
from pyatv.support import http

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


def pairing_url(zeroconf, pairing_code):
    service = zeroconf.registered_services[0]
    return (
        f"http://127.0.0.1:{service.port}/"
        + f"pair?pairingcode={pairing_code}&servicename=test"
    )


@pytest.fixture
def mock_random():
    pairing.random.getrandbits = lambda x: RANDOM_128_BITS


@pytest.fixture
async def mock_pairing(event_loop):
    obj = MagicMock()

    service = ManualService(None, Protocol.DMAP, 0, {})
    config = AppleTV("Apple TV", "127.0.0.1")
    config.add_service(service)
    zeroconf = zeroconf_stub.stub(pairing)

    async def _start(pin_code=PIN_CODE, pairing_guid=PAIRING_GUID, name=REMOTE_NAME):
        options = {"zeroconf": zeroconf}
        if pairing_guid:
            options["pairing_guid"] = pairing_guid
        if name:
            options["name"] = name

        obj.pairing = pairing.DmapPairingHandler(
            config, service, await http.create_session(), event_loop, **options
        )
        await obj.pairing.begin()
        obj.pairing.pin(pin_code)
        return obj.pairing, zeroconf, service

    yield _start
    await obj.pairing.finish()
    await obj.pairing.close()


@pytest.mark.asyncio
async def test_zeroconf_service_published(mock_pairing):
    _, zeroconf, service = await mock_pairing()

    assert len(zeroconf.registered_services) == 1, "no zeroconf service registered"

    service = zeroconf.registered_services[0]
    assert service.properties["DvNm"] == REMOTE_NAME, "remote name does not match"


@pytest.mark.asyncio
async def test_succesful_pairing(mock_pairing):
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


@pytest.mark.asyncio
async def test_successful_pairing_random_pairing_guid_generated(
    mock_random, mock_pairing
):
    pairing, zeroconf, service = await mock_pairing(pairing_guid=None)

    url = pairing_url(zeroconf, RANDOM_PAIRING_CODE)
    await utils.simple_get(url)

    await pairing.finish()

    assert service.credentials == RANDOM_PAIRING_GUID


@pytest.mark.asyncio
async def test_succesful_pairing_with_any_pin(mock_pairing):
    _, zeroconf, _ = await mock_pairing(pin_code=None)

    url = pairing_url(zeroconf, "invalid_pairing_code")
    _, status = await utils.simple_get(url)

    assert status == 200


@pytest.mark.asyncio
async def test_succesful_pairing_with_pin_leadering_zeros(mock_pairing):
    _, zeroconf, _ = await mock_pairing(pin_code=PIN_CODE3, pairing_guid=PAIRING_GUID3)

    url = pairing_url(zeroconf, PAIRING_CODE3)
    _, status = await utils.simple_get(url)

    assert status == 200


@pytest.mark.asyncio
async def test_pair_custom_pairing_guid(mock_pairing):
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


@pytest.mark.asyncio
async def test_failed_pairing(mock_pairing):
    _, zeroconf, _ = await mock_pairing()

    url = pairing_url(zeroconf, "wrong")
    data, status = await utils.simple_get(url)

    assert status == 500
