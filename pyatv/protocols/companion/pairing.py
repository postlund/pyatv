"""Device pairing and derivation of encryption keys."""

import logging
from typing import Optional

from pyatv import exceptions
from pyatv.auth.hap_srp import SRPAuthHandler
from pyatv.core import Core
from pyatv.interface import PairingHandler
from pyatv.protocols.companion.auth import CompanionPairSetupProcedure
from pyatv.protocols.companion.connection import CompanionConnection
from pyatv.protocols.companion.protocol import CompanionProtocol
from pyatv.support import error_handler

_LOGGER = logging.getLogger(__name__)


class CompanionPairingHandler(PairingHandler):
    """Pairing handler used to pair the Companion link protocol."""

    def __init__(self, core: Core, **kwargs):
        """Initialize a new CompanionPairingHandler."""
        super().__init__(core.session_manager, core.service)
        self._name: str = kwargs.get("name", "pyatv")
        self.connection = CompanionConnection(
            core.loop, str(core.config.address), core.service.port, None
        )
        self.srp = SRPAuthHandler()
        self.protocol = CompanionProtocol(self.connection, self.srp, core.service)
        self.pairing_procedure = CompanionPairSetupProcedure(self.protocol, self.srp)
        self.pin_code: Optional[str] = None
        self._settings = core.settings
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
                "",  # username required but not used
                self.pin_code,
                self._name,
            )
        )
        self._settings.protocols.companion.credentials = self.service.credentials
        self._has_paired = True

    @property
    def device_provides_pin(self) -> bool:
        """Return True if remote device presents PIN code, else False."""
        return True

    def pin(self, pin: int) -> None:
        """Pin code used for pairing."""
        self.pin_code = str(pin).zfill(4)
        _LOGGER.debug("Companion PIN changed to %s", self.pin_code)
