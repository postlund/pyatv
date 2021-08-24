"""AirPlay device authentication tests with fake device."""

import binascii

import pytest

from pyatv.airplay.auth_legacy import (
    AirPlayPairSetupProcedure,
    AirPlayPairVerifyProcedure,
    HapCredentials,
)
from pyatv.airplay.srp import SRPAuthHandler
from pyatv.exceptions import AuthenticationError, NotSupportedError

from tests.fake_device.airplay import DEVICE_AUTH_KEY, DEVICE_IDENTIFIER, DEVICE_PIN

IDENTIFIER = 8 * b"\x11"
INVALID_AUTH_KEY = 32 * b"\x00"

pytestmark = pytest.mark.asyncio


def new_credentials(identifier, seed) -> HapCredentials:
    return HapCredentials(b"", seed, b"", identifier)


async def test_verify_invalid(airplay_device, client_connection):
    srp = SRPAuthHandler(new_credentials(IDENTIFIER, INVALID_AUTH_KEY))
    srp.initialize()

    verifier = AirPlayPairVerifyProcedure(client_connection, srp)
    with pytest.raises(AuthenticationError):
        await verifier.verify_credentials()


async def test_verify_authenticated(airplay_device, client_connection):
    srp = SRPAuthHandler(
        new_credentials(IDENTIFIER, binascii.unhexlify(DEVICE_AUTH_KEY))
    )
    srp.initialize()

    verifier = AirPlayPairVerifyProcedure(client_connection, srp)
    assert await verifier.verify_credentials()


async def test_verify_has_no_encryption_keys(airplay_device, client_connection):
    srp = SRPAuthHandler(
        new_credentials(IDENTIFIER, binascii.unhexlify(DEVICE_AUTH_KEY))
    )
    srp.initialize()

    verifier = AirPlayPairVerifyProcedure(client_connection, srp)
    with pytest.raises(NotSupportedError):
        assert verifier.encryption_keys()


async def test_pairing_failed(airplay_device, client_connection):
    srp = SRPAuthHandler(new_credentials(IDENTIFIER, INVALID_AUTH_KEY))
    srp.initialize()

    pairing_procedure = AirPlayPairSetupProcedure(client_connection, srp)
    await pairing_procedure.start_pairing()
    with pytest.raises(AuthenticationError):
        await pairing_procedure.finish_pairing(DEVICE_IDENTIFIER, DEVICE_PIN)


async def test_pairing_successful(airplay_device, client_connection):
    srp = SRPAuthHandler(
        new_credentials(IDENTIFIER, binascii.unhexlify(DEVICE_AUTH_KEY))
    )
    srp.initialize()

    pairing_procedure = AirPlayPairSetupProcedure(client_connection, srp)
    await pairing_procedure.start_pairing()
    assert await pairing_procedure.finish_pairing(DEVICE_IDENTIFIER, DEVICE_PIN)
