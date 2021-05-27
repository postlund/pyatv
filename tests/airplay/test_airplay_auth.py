"""AirPlay device authentication tests with fake device."""

import binascii

import pytest

from pyatv.airplay.auth import AuthenticationVerifier, DeviceAuthenticator
from pyatv.airplay.srp import SRPAuthHandler
from pyatv.exceptions import AuthenticationError

from tests.fake_device.airplay import DEVICE_AUTH_KEY, DEVICE_IDENTIFIER, DEVICE_PIN

INVALID_AUTH_KEY = 32 * b"\x00"

pytestmark = pytest.mark.asyncio


async def test_verify_invalid2(airplay_device, client_connection):
    srp = SRPAuthHandler()
    srp.initialize(INVALID_AUTH_KEY)

    verifier = AuthenticationVerifier(client_connection, srp)
    with pytest.raises(AuthenticationError):
        await verifier.verify_authed()


async def test_verify_invalid(airplay_device, client_connection):
    srp = SRPAuthHandler()
    srp.initialize(INVALID_AUTH_KEY)

    verifier = AuthenticationVerifier(client_connection, srp)
    with pytest.raises(AuthenticationError):
        await verifier.verify_authed()


async def test_verify_authenticated(airplay_device, client_connection):
    srp = SRPAuthHandler()
    srp.initialize(binascii.unhexlify(DEVICE_AUTH_KEY))

    verifier = AuthenticationVerifier(client_connection, srp)
    assert await verifier.verify_authed()


async def test_auth_failed(airplay_device, client_connection):
    srp = SRPAuthHandler()
    srp.initialize(INVALID_AUTH_KEY)

    authenticator = DeviceAuthenticator(client_connection, srp)
    await authenticator.start_authentication()
    with pytest.raises(AuthenticationError):
        await authenticator.finish_authentication(DEVICE_IDENTIFIER, DEVICE_PIN)


async def test_auth_successful(airplay_device, client_connection):
    srp = SRPAuthHandler()
    srp.initialize(binascii.unhexlify(DEVICE_AUTH_KEY))

    authenticator = DeviceAuthenticator(client_connection, srp)
    await authenticator.start_authentication()
    assert await authenticator.finish_authentication(DEVICE_IDENTIFIER, DEVICE_PIN)
