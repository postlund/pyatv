"""Pick authentication type based on device support."""
from enum import Enum
import logging
from typing import Tuple

from pyatv import exceptions
from pyatv.airplay.auth.legacy import (
    AirPlayLegacyPairSetupProcedure,
    AirPlayLegacyPairVerifyProcedure,
)
from pyatv.airplay.srp import SRPAuthHandler, new_credentials
from pyatv.auth.hap_pairing import (
    NO_CREDENTIALS,
    HapCredentials,
    PairSetupProcedure,
    PairVerifyProcedure,
)
from pyatv.support.http import HttpConnection

_LOGGER = logging.getLogger(__name__)

# pylint: disable=invalid-name


class AuthenticationType(Enum):
    """Supported authentication type."""

    Legacy = 1
    """Legacy SRP based authentication."""


# pylint: enable=invalid-name


class NullPairVerifyProcedure:
    """Null implementation for Pair-Verify when no verification is needed."""

    async def verify_credentials(self) -> bool:
        """Verify if credentials are valid."""
        _LOGGER.debug("Performing null Pair-Verify")
        return True

    @staticmethod
    def encryption_keys() -> Tuple[str, str]:
        """Return derived encryption keys."""
        raise exceptions.NotSupportedError(
            "encryption keys not supported by null implementation"
        )


def pair_setup(
    auth_type: AuthenticationType, connection: HttpConnection
) -> PairSetupProcedure:
    """Return procedure object used for Pair-Setup."""
    credentials = new_credentials()

    _LOGGER.debug(
        "Setting up new AirPlay Pair-Setup procedure with credentials %s", credentials
    )
    srp = SRPAuthHandler(credentials)
    srp.initialize()
    return AirPlayLegacyPairSetupProcedure(connection, srp)


def pair_verify(
    credentials: HapCredentials, connection: HttpConnection
) -> PairVerifyProcedure:
    """Return procedure object used for Pair-Verify."""
    if credentials == NO_CREDENTIALS:
        return NullPairVerifyProcedure()

    _LOGGER.debug(
        "Setting up new AirPlay Pair-Verify procedure with credentials %s", credentials
    )
    srp = SRPAuthHandler(credentials)
    srp.initialize()
    return AirPlayLegacyPairVerifyProcedure(connection, srp)
