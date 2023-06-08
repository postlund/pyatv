"""Functional credential verification tests using the API with a fake AirPlay Apple TV."""

from contextlib import nullcontext as does_not_raise

import pytest

from pyatv.auth.hap_pairing import TRANSIENT_CREDENTIALS, parse_credentials
from pyatv.auth.server_auth import CLIENT_CREDENTIALS
from pyatv.const import Protocol
from pyatv.exceptions import AuthenticationError
from pyatv.protocols.airplay.auth import pair_verify
from pyatv.support import http

from tests.fake_device.airplay import DEVICE_CREDENTIALS

pytestmark = pytest.mark.asyncio


@pytest.mark.parametrize(
    "credentials, expectation",
    [
        (parse_credentials(DEVICE_CREDENTIALS), does_not_raise()),
        (
            parse_credentials(f"{8 * '00'}:{32 * '11'}"),
            pytest.raises(AuthenticationError),
        ),
        (parse_credentials(CLIENT_CREDENTIALS), does_not_raise()),
        (
            parse_credentials(f"{32 * '00'}:{32 * '11'}:{36 * '22'}:{36 * '33'}"),
            pytest.raises(AuthenticationError),
        ),
        (TRANSIENT_CREDENTIALS, does_not_raise()),
    ],
)
async def test_verify(airplay_conf, credentials, expectation):
    connection = await http.http_connect(
        str(airplay_conf.address), airplay_conf.get_service(Protocol.AirPlay).port
    )
    verifier = pair_verify(credentials, connection)
    with expectation:
        await verifier.verify_credentials()
    connection.close()
