"""Device pairing and derivation of encryption keys."""

import binascii
from collections import namedtuple
import logging
from typing import Optional

from pyatv import conf, exceptions
from pyatv.airplay.auth import DeviceAuthenticator
from pyatv.airplay.srp import SRPAuthHandler, new_credentials
from pyatv.const import Protocol
from pyatv.interface import PairingHandler
from pyatv.support import error_handler, net
from pyatv.support.http import HttpConnection, http_connect

_LOGGER = logging.getLogger(__name__)

AuthData = namedtuple("AuthData", "identifier seed credentials")


class AirPlayPairingHandler(PairingHandler):
    """Base class for API used to pair with an Apple TV."""

    def __init__(
        self, config: conf.AppleTV, session_manager: net.ClientSessionManager, _
    ) -> None:
        """Initialize a new MrpPairingHandler."""
        super().__init__(session_manager, config.get_service(Protocol.AirPlay))
        self.http: Optional[HttpConnection] = None
        self.address: str = str(config.address)
        self.authenticator: Optional[DeviceAuthenticator] = None
        self.auth_data = self._setup_credentials()
        self.pin_code: Optional[str] = None
        self._has_paired: bool = False

    def _setup_credentials(self) -> AuthData:
        credentials = self.service.credentials

        # If service has credentials, use those. Otherwise generate new.
        if credentials is None:
            identifier, seed = new_credentials()
            credentials = f"{identifier}:{seed.decode().upper()}"
        else:
            identifier, seed = credentials.split(":", maxsplit=1)
        return AuthData(identifier, seed, credentials)

    @property
    def has_paired(self) -> bool:
        """If a successful pairing has been performed."""
        return self._has_paired

    async def close(self) -> None:
        """Call to free allocated resources after pairing."""
        await super().close()
        if self.http:
            self.http.close()

    async def begin(self) -> None:
        """Start pairing process."""
        _LOGGER.debug(
            "Starting AirPlay pairing with credentials %s", self.auth_data.credentials
        )

        srp: SRPAuthHandler = SRPAuthHandler()
        srp.initialize(binascii.unhexlify(self.auth_data.seed))

        self.http = await http_connect(self.address, self.service.port)
        self.authenticator = DeviceAuthenticator(self.http, srp)

        self._has_paired = False
        return await error_handler(
            self.authenticator.start_authentication, exceptions.PairingError
        )

    async def finish(self) -> None:
        """Stop pairing process."""
        if not self.authenticator:
            raise exceptions.PairingError("pairing was not started")
        if not self.pin_code:
            raise exceptions.PairingError("no pin given")

        await error_handler(
            self.authenticator.finish_authentication,
            exceptions.PairingError,
            self.auth_data.identifier,
            self.pin_code,
        )

        self.service.credentials = self.auth_data.credentials
        self._has_paired = True

    def pin(self, pin: int) -> None:
        """Pin code used for pairing."""
        self.pin_code = str(pin).zfill(4)
        _LOGGER.debug("AirPlay PIN changed to %s", self.pin_code)

    @property
    def device_provides_pin(self) -> bool:
        """Return True if remote device presents PIN code, else False."""
        return True
