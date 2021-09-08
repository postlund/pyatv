"""Unit tests for legacy device authentication."""

import binascii

import pytest

from pyatv.exceptions import AuthenticationError, NotSupportedError
from pyatv.protocols.airplay.auth.legacy import (
    AirPlayLegacyPairSetupProcedure,
    AirPlayLegacyPairVerifyProcedure,
    HapCredentials,
)
from pyatv.protocols.airplay.srp import LegacySRPAuthHandler

from tests.fake_device.airplay import DEVICE_AUTH_KEY, DEVICE_IDENTIFIER, DEVICE_PIN

IDENTIFIER = 8 * "11"
INVALID_AUTH_KEY = 32 * "00"

pytestmark = pytest.mark.asyncio


def new_credentials(identifier: str, seed: str) -> HapCredentials:
    return HapCredentials(
        b"", binascii.unhexlify(seed), b"", binascii.unhexlify(identifier)
    )


async def test_verify_invalid(airplay_device, client_connection):
    srp = LegacySRPAuthHandler(new_credentials(IDENTIFIER, INVALID_AUTH_KEY))
    srp.initialize()

    verifier = AirPlayLegacyPairVerifyProcedure(client_connection, srp)
    with pytest.raises(AuthenticationError):
        await verifier.verify_credentials()


async def test_verify_authenticated(airplay_device, client_connection):
    srp = LegacySRPAuthHandler(new_credentials(IDENTIFIER, DEVICE_AUTH_KEY))
    srp.initialize()

    verifier = AirPlayLegacyPairVerifyProcedure(client_connection, srp)
    assert not await verifier.verify_credentials()


async def test_verify_has_no_encryption_keys(airplay_device, client_connection):
    srp = LegacySRPAuthHandler(new_credentials(IDENTIFIER, DEVICE_AUTH_KEY))
    srp.initialize()

    verifier = AirPlayLegacyPairVerifyProcedure(client_connection, srp)
    with pytest.raises(NotSupportedError):
        assert verifier.encryption_keys("salt", "output", "input")


async def test_pairing_failed(airplay_device, client_connection):
    srp = LegacySRPAuthHandler(new_credentials(IDENTIFIER, INVALID_AUTH_KEY))
    srp.initialize()

    pairing_procedure = AirPlayLegacyPairSetupProcedure(client_connection, srp)
    await pairing_procedure.start_pairing()
    with pytest.raises(AuthenticationError):
        await pairing_procedure.finish_pairing(DEVICE_IDENTIFIER, DEVICE_PIN)


async def test_pairing_successful(airplay_device, client_connection):
    srp = LegacySRPAuthHandler(new_credentials(DEVICE_IDENTIFIER, DEVICE_AUTH_KEY))
    srp.initialize()

    pairing_procedure = AirPlayLegacyPairSetupProcedure(client_connection, srp)
    await pairing_procedure.start_pairing()
    assert await pairing_procedure.finish_pairing(DEVICE_IDENTIFIER, DEVICE_PIN)
