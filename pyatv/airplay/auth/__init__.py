"""Pick authentication type based on device support."""
from enum import Enum
import logging
from typing import Tuple

from pyatv import exceptions
from pyatv.airplay.auth.hap import (
    AirPlayHapPairSetupProcedure,
    AirPlayHapPairVerifyProcedure,
)
from pyatv.airplay.auth.legacy import (
    AirPlayLegacyPairSetupProcedure,
    AirPlayLegacyPairVerifyProcedure,
)
from pyatv.airplay.srp import LegacySRPAuthHandler, new_credentials
from pyatv.auth.hap_pairing import (
    NO_CREDENTIALS,
    HapCredentials,
    PairSetupProcedure,
    PairVerifyProcedure,
)
from pyatv.auth.hap_session import HAPSession
from pyatv.auth.hap_srp import SRPAuthHandler
from pyatv.support.http import HttpConnection

_LOGGER = logging.getLogger(__name__)

# pylint: disable=invalid-name


class AuthenticationType(Enum):
    """Supported authentication type."""

    Legacy = 1
    """Legacy SRP based authentication."""

    HAP = 2
    """Authentication based on HAP (Home-Kit)."""


# pylint: enable=invalid-name


class NullPairVerifyProcedure:
    """Null implementation for Pair-Verify when no verification is needed."""

    async def verify_credentials(self) -> bool:
        """Verify if credentials are valid."""
        _LOGGER.debug("Performing null Pair-Verify")
        return False

    @staticmethod
    def encryption_keys() -> Tuple[str, str]:
        """Return derived encryption keys."""
        raise exceptions.NotSupportedError(
            "encryption keys not supported by null implementation"
        )


def _get_auth_type(credentials: HapCredentials) -> AuthenticationType:
    if (
        credentials.ltpk == b""
        and credentials.ltsk != b""
        and credentials.atv_id == b""
        and credentials.client_id != b""
    ):
        return AuthenticationType.Legacy
    return AuthenticationType.HAP


def pair_setup(
    auth_type: AuthenticationType, connection: HttpConnection
) -> PairSetupProcedure:
    """Return procedure object used for Pair-Setup."""
    _LOGGER.debug("Setting up new AirPlay Pair-Setup procedure with type %s", auth_type)

    if auth_type == AuthenticationType.Legacy:
        srp = LegacySRPAuthHandler(new_credentials())
        srp.initialize()
        return AirPlayLegacyPairSetupProcedure(connection, srp)

    # HAP
    srp = SRPAuthHandler()
    srp.initialize()
    return AirPlayHapPairSetupProcedure(connection, srp)


def pair_verify(
    credentials: HapCredentials, connection: HttpConnection
) -> PairVerifyProcedure:
    """Return procedure object used for Pair-Verify."""
    if credentials == NO_CREDENTIALS:
        return NullPairVerifyProcedure()

    auth_type = _get_auth_type(credentials)

    _LOGGER.debug(
        "Setting up new AirPlay Pair-Verify procedure with type %s", auth_type
    )

    if auth_type == AuthenticationType.Legacy:
        srp = LegacySRPAuthHandler(credentials)
        srp.initialize()
        return AirPlayLegacyPairVerifyProcedure(connection, srp)

    # HAP
    srp = SRPAuthHandler()
    srp.initialize()
    return AirPlayHapPairVerifyProcedure(connection, srp, credentials)


async def verify_connection(
    credentials: HapCredentials, connection: HttpConnection
) -> None:
    """Perform Pair-Verify on a connection and enable encryption."""
    verifier = pair_verify(credentials, connection)
    has_encryption_keys = await verifier.verify_credentials()

    if has_encryption_keys:
        output_key, input_key = verifier.encryption_keys()

        session = HAPSession()
        session.enable(output_key, input_key)
        connection.receive_processor = session.decrypt
        connection.send_processor = session.encrypt
