"""Device pairing and derivation of encryption keys."""

import binascii
import logging
from typing import Optional

from pyatv import conf, exceptions
from pyatv.airplay.auth import AirPlayPairingProcedure
from pyatv.airplay.srp import LegacyCredentials, SRPAuthHandler, new_credentials
from pyatv.const import Protocol
from pyatv.interface import PairingHandler
from pyatv.support import error_handler
from pyatv.support.http import ClientSessionManager, HttpConnection, http_connect

_LOGGER = logging.getLogger(__name__)


class AirPlayPairingHandler(PairingHandler):
    """Base class for API used to pair with an Apple TV."""

    def __init__(
        self, config: conf.AppleTV, session_manager: ClientSessionManager, _
    ) -> None:
        """Initialize a new MrpPairingHandler."""
        super().__init__(session_manager, config.get_service(Protocol.AirPlay))
        self.http: Optional[HttpConnection] = None
        self.address: str = str(config.address)
        self.pairing_procedure: Optional[AirPlayPairingProcedure] = None
        self.credentials: LegacyCredentials = self._setup_credentials()
        self.pin_code: Optional[str] = None
        self._has_paired: bool = False

    def _setup_credentials(self) -> LegacyCredentials:
        # If service has credentials, use those. Otherwise generate new.
        if self.service.credentials is None:
            return new_credentials()
        return LegacyCredentials.parse(self.service.credentials)

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
        _LOGGER.debug("Starting AirPlay pairing with credentials %s", self.credentials)

        srp: SRPAuthHandler = SRPAuthHandler(self.credentials)
        srp.initialize()

        self.http = await http_connect(self.address, self.service.port)
        self.pairing_procedure = AirPlayPairingProcedure(self.http, srp)

        self._has_paired = False
        return await error_handler(
            self.pairing_procedure.start_pairing, exceptions.PairingError
        )

    async def finish(self) -> None:
        """Stop pairing process."""
        if not self.pairing_procedure:
            raise exceptions.PairingError("pairing was not started")
        if not self.pin_code:
            raise exceptions.PairingError("no pin given")

        self.service.credentials = str(
            await error_handler(
                self.pairing_procedure.finish_pairing,
                exceptions.PairingError,
                binascii.hexlify(self.credentials.identifier).decode("ascii").upper(),
                self.pin_code,
            )
        )
        self._has_paired = True

    def pin(self, pin: int) -> None:
        """Pin code used for pairing."""
        self.pin_code = str(pin).zfill(4)
        _LOGGER.debug("AirPlay PIN changed to %s", self.pin_code)

    @property
    def device_provides_pin(self) -> bool:
        """Return True if remote device presents PIN code, else False."""
        return True
