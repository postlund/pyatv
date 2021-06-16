"""Device pairing and derivation of encryption keys."""
import asyncio
import logging
from typing import Optional, cast

from pyatv import exceptions
from pyatv.companion.auth import CompanionPairingProcedure
from pyatv.companion.connection import CompanionConnection
from pyatv.companion.protocol import CompanionProtocol
from pyatv.conf import CompanionService
from pyatv.const import Protocol
from pyatv.interface import PairingHandler
from pyatv.support import error_handler
from pyatv.support.hap_srp import SRPAuthHandler
from pyatv.support.http import ClientSessionManager

_LOGGER = logging.getLogger(__name__)


class CompanionPairingHandler(PairingHandler):
    """Pairing handler used to pair the Companion link protocol."""

    def __init__(
        self, config, session: ClientSessionManager, loop: asyncio.AbstractEventLoop
    ):
        """Initialize a new CompanionPairingHandler."""
        super().__init__(session, config.get_service(Protocol.Companion))
        self.connection = CompanionConnection(
            loop, config.address, self.service.port, None
        )
        self.srp = SRPAuthHandler()
        self.protocol = CompanionProtocol(
            self.connection, self.srp, cast(CompanionService, self.service)
        )
        self.pairing_procedure = CompanionPairingProcedure(self.protocol, self.srp)
        self.pin_code: Optional[str] = None
        self._has_paired: bool = False

    async def close(self) -> None:
        """Call to free allocated resources after pairing."""
        self.protocol.stop()
        await super().close()

    @property
    def has_paired(self) -> bool:
        """If a successful pairing has been performed."""
        return self._has_paired

    async def begin(self) -> None:
        """Start pairing process."""
        _LOGGER.debug("Start pairing Companion")
        await error_handler(
            self.pairing_procedure.start_pairing, exceptions.PairingError
        )

    async def finish(self) -> None:
        """Stop pairing process."""
        _LOGGER.debug("Finish pairing Companion")
        if not self.pin_code:
            raise exceptions.PairingError("no pin given")

        self.service.credentials = str(
            await error_handler(
                self.pairing_procedure.finish_pairing,
                exceptions.PairingError,
                self.pin_code,
            )
        )
        self._has_paired = True

    @property
    def device_provides_pin(self) -> bool:
        """Return True if remote device presents PIN code, else False."""
        return True

    def pin(self, pin: int) -> None:
        """Pin code used for pairing."""
        self.pin_code = str(pin).zfill(4)
        _LOGGER.debug("Companion PIN changed to %s", self.pin_code)
