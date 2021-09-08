"""Functional pairing tests using the API with a fake AirPlay Apple TV."""

import asyncio
import binascii
from unittest.mock import patch

import pytest

from pyatv import exceptions, pair
from pyatv.auth.hap_pairing import parse_credentials
from pyatv.const import Protocol

from tests.fake_device.airplay import (
    DEVICE_AUTH_KEY,
    DEVICE_CREDENTIALS,
    DEVICE_IDENTIFIER,
    DEVICE_PIN,
)

pytestmark = pytest.mark.asyncio


def predetermined_key(num):
    """Return random data corresponding to hardcoded AirPlay keys."""
    if num == 8:
        return binascii.unhexlify(DEVICE_IDENTIFIER)
    return binascii.unhexlify(DEVICE_AUTH_KEY)


@pytest.fixture(autouse=True)
def require_auth(airplay_usecase):
    airplay_usecase.airplay_require_authentication()


async def perform_pairing(conf, pin=DEVICE_PIN):
    pairing = await pair(conf, Protocol.AirPlay, asyncio.get_event_loop())

    assert pairing.device_provides_pin

    await pairing.begin()
    if pin:
        pairing.pin(pin)

    assert not pairing.has_paired

    await pairing.finish()
    assert pairing.has_paired
    assert parse_credentials(
        conf.get_service(Protocol.AirPlay).credentials
    ) == parse_credentials(DEVICE_CREDENTIALS)


async def test_pairing_exception_invalid_pin(airplay_conf):
    with pytest.raises(exceptions.PairingError):
        await perform_pairing(airplay_conf, 9999)


async def test_pairing_exception_no_pin(airplay_conf):
    with pytest.raises(exceptions.PairingError):
        await perform_pairing(airplay_conf, None)


async def test_pairing_with_device_new_credentials(airplay_conf):
    # Using patch as decorator does not seem to work with python < 3.8, but can be
    # worked around using asynctest. This is however the only async test using patch
    # for now, so lets use a context manager and introduce asynctest when needed.
    # Source: https://github.com/pytest-dev/pytest-asyncio/issues/130
    with patch("pyatv.protocols.airplay.srp.urandom") as rand_func:
        rand_func.side_effect = predetermined_key
        await perform_pairing(airplay_conf)
