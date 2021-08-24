"""Abstraction for authentication based on HAP/SRP."""
import binascii
from typing import Optional, Tuple

from pyatv import exceptions


# pylint: disable=too-few-public-methods
class HapCredentials:
    """Identifiers and encryption keys used by HAP."""

    def __init__(
        self, ltpk: bytes, ltsk: bytes, atv_id: bytes, client_id: bytes
    ) -> None:
        """Initialize a new Credentials."""
        self.ltpk: bytes = ltpk
        self.ltsk: bytes = ltsk
        self.atv_id: bytes = atv_id
        self.client_id: bytes = client_id

    def __eq__(self, other: object) -> bool:
        """Return if two instances of HapCredentials are equal."""
        if isinstance(other, HapCredentials):
            return str(other) == str(self)
        return False

    def __str__(self) -> str:
        """Return a string representation of credentials."""
        return ":".join(
            [
                binascii.hexlify(self.ltpk).decode("utf-8"),
                binascii.hexlify(self.ltsk).decode("utf-8"),
                binascii.hexlify(self.atv_id).decode("utf-8"),
                binascii.hexlify(self.client_id).decode("utf-8"),
            ]
        )


class PairSetupProcedure:
    """Perform pair setup procedure to authenticate a new device."""

    async def start_pairing(self) -> None:
        """Start the pairing process.

        This method will show the expected PIN on screen.
        """

    async def finish_pairing(self, username: str, pin_code: int) -> HapCredentials:
        """Finish pairing process.

        A username and the PIN code (usually shown on screen) must be provided.
        """


class PairVerifyProcedure:
    """Verify if credentials are valid and derive encryption keys."""

    async def verify_credentials(self) -> bool:
        """Verify if credentials are valid and returns True if keys are generated."""

    def encryption_keys(
        self, salt: str, output_info: str, input_info: str
    ) -> Tuple[str, str]:
        """Return derived encryption keys."""


NO_CREDENTIALS = HapCredentials(b"", b"", b"", b"")


def parse_credentials(detail_string: Optional[str]) -> HapCredentials:
    """Parse a string represention of HapCredentials."""
    if detail_string is None:
        return NO_CREDENTIALS

    split = detail_string.split(":")

    # Compatibility with "legacy credentials" used by AirPlay where seed is stored
    # as LTSK and identifier as client_id (others are empty).
    if len(split) == 2:
        client_id = binascii.unhexlify(split[0])
        ltsk = binascii.unhexlify(split[1])
        return HapCredentials(b"", ltsk, b"", client_id)
    if len(split) == 4:
        ltpk = binascii.unhexlify(split[0])
        ltsk = binascii.unhexlify(split[1])
        atv_id = binascii.unhexlify(split[2])
        client_id = binascii.unhexlify(split[3])
        return HapCredentials(ltpk, ltsk, atv_id, client_id)

    raise exceptions.InvalidCredentialsError("invalid credentials: " + detail_string)
