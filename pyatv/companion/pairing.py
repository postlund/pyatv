"""Device pairing and derivation of encryption keys."""

import asyncio
import logging

from pyatv import exceptions
from pyatv.const import Protocol
from pyatv.interface import PairingHandler
from pyatv.companion.connection import CompanionConnection
from pyatv.companion.auth import CompanionPairingProcedure
from pyatv.companion.protocol import CompanionProtocol
from pyatv.companion.srp import SRPAuthHandler
from pyatv.support import error_handler, log_binary

_LOGGER = logging.getLogger(__name__)


class CompanionPairingHandler(PairingHandler):
    """Pairing handler used to pair the Companion link protocol."""

    def __init__(self, config, session, loop):
        """Initialize a new CompanionPairingHandler."""
        super().__init__(session, config.get_service(Protocol.Companion))
        self.connection = CompanionConnection(loop, config.address, self.service.port)
        self.srp = SRPAuthHandler()
        self.protocol = CompanionProtocol(self.connection, self.srp, self.service)
        self.pairing_procedure = CompanionPairingProcedure(self.protocol, self.srp)
        self.pin_code = None
        self._has_paired = False

    async def close(self):
        """Call to free allocated resources after pairing."""
        self.protocol.stop()
        await super().close()

    @property
    def has_paired(self):
        """If a successful pairing has been performed."""
        return self._has_paired

    async def begin(self):
        """Start pairing process."""
        _LOGGER.debug("Start pairing Companion")
        await error_handler(
            self.pairing_procedure.start_pairing, exceptions.PairingError
        )

    async def finish(self):
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
    def device_provides_pin(self):
        """Return True if remote device presents PIN code, else False."""
        return True

    def pin(self, pin):
        """Pin code used for pairing."""
        self.pin_code = str(pin).zfill(4)
        _LOGGER.debug("Companion PIN changed to %s", self.pin_code)
