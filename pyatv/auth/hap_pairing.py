"""Abstraction for authentication based on HAP/SRP."""

from abc import ABC, abstractmethod
import binascii
from enum import Enum, auto
from typing import Optional, Tuple

from pyatv import exceptions

# pylint: disable=invalid-name


class AuthenticationType(Enum):
    """Supported authentication type."""

    Null = auto()
    """No authentication (just pass through)."""

    Legacy = auto()
    """Legacy SRP based authentication."""

    HAP = auto()
    """Authentication based on HAP (Home-Kit)."""

    Transient = auto()
    """Authentication based on transient HAP (Home-Kit)."""


# pylint: enable=invalid-name


class HapCredentials:
    """Identifiers and encryption keys used by HAP."""

    def __init__(
        self,
        ltpk: bytes = b"",
        ltsk: bytes = b"",
        atv_id: bytes = b"",
        client_id: bytes = b"",
    ) -> None:
        """Initialize a new Credentials."""
        self.ltpk: bytes = ltpk
        self.ltsk: bytes = ltsk
        self.atv_id: bytes = atv_id
        self.client_id: bytes = client_id
        self.type: AuthenticationType = self._get_auth_type()

    def _get_auth_type(self) -> AuthenticationType:
        if (
            self.ltpk == b""
            and self.ltsk == b""
            and self.atv_id == b""
            and self.client_id == b""
        ):
            return AuthenticationType.Null
        if self.ltpk == b"transient":
            return AuthenticationType.Transient
        if (
            self.ltpk == b""
            and self.ltsk != b""
            and self.atv_id == b""
            and self.client_id != b""
        ):
            return AuthenticationType.Legacy
        if self.ltpk and self.ltsk and self.atv_id and self.client_id:
            return AuthenticationType.HAP

        raise exceptions.InvalidCredentialsError("invalid credentials type")

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


class PairSetupProcedure(ABC):
    """Perform pair setup procedure to authenticate a new device."""

    @abstractmethod
    async def start_pairing(self) -> None:
        """Start the pairing process.

        This method will show the expected PIN on screen.
        """

    @abstractmethod
    async def finish_pairing(
        self, username: str, pin_code: int, display_name: Optional[str]
    ) -> HapCredentials:
        """Finish pairing process.

        A username and the PIN code (usually shown on screen) must be provided.
        """


class PairVerifyProcedure(ABC):
    """Verify if credentials are valid and derive encryption keys."""

    @abstractmethod
    async def verify_credentials(self) -> bool:
        """Verify if credentials are valid and returns True if keys are generated."""

    @abstractmethod
    def encryption_keys(
        self, salt: str, output_info: str, input_info: str
    ) -> Tuple[bytes, bytes]:
        """Return derived encryption keys."""


NO_CREDENTIALS = HapCredentials()
TRANSIENT_CREDENTIALS = HapCredentials(b"transient")


def parse_credentials(detail_string: Optional[str]) -> HapCredentials:
    """Parse a string representation of HapCredentials."""
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
