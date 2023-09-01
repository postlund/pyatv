"""Device pairing and derivation of encryption keys."""

import logging

from pyatv import exceptions
from pyatv.auth.hap_pairing import parse_credentials
from pyatv.auth.hap_srp import SRPAuthHandler
from pyatv.core import Core
from pyatv.interface import PairingHandler
from pyatv.protocols.mrp.auth import MrpPairSetupProcedure, MrpPairVerifyProcedure
from pyatv.protocols.mrp.connection import MrpConnection
from pyatv.protocols.mrp.protocol import MrpProtocol
from pyatv.support import error_handler

_LOGGER = logging.getLogger(__name__)


class MrpPairingHandler(PairingHandler):
    """Base class for API used to pair with an Apple TV."""

    def __init__(self, core: Core, **kwargs):
        """Initialize a new MrpPairingHandler."""
        super().__init__(core.session_manager, core.service)
        self.connection = MrpConnection(
            core.config.address, self.service.port, core.loop
        )
        self.srp = SRPAuthHandler()
        self.protocol = MrpProtocol(
            self.connection, self.srp, self.service, core.settings.info
        )
        self.pairing_procedure = MrpPairSetupProcedure(self.protocol, self.srp)
        self.pin_code = None
        self._settings = core.settings
        self._has_paired = False

    async def close(self):
        """Call to free allocated resources after pairing."""
        self.connection.close()
        await super().close()

    @property
    def has_paired(self):
        """If a successful pairing has been performed."""
        return self._has_paired

    async def begin(self):
        """Start pairing process."""
        return await error_handler(
            self.pairing_procedure.start_pairing, exceptions.PairingError
        )

    async def finish(self):
        """Stop pairing process."""
        if not self.pin_code:
            raise exceptions.PairingError("no pin given")

        credentials = str(
            await error_handler(
                self.pairing_procedure.finish_pairing,
                exceptions.PairingError,
                "",  # username required but not used
                self.pin_code,
                None,
            )
        )

        _LOGGER.debug("Verifying credentials %s", credentials)

        verifier = MrpPairVerifyProcedure(
            self.protocol, self.srp, parse_credentials(credentials)
        )
        await error_handler(verifier.verify_credentials, exceptions.PairingError)

        self.service.credentials = credentials
        self._settings.protocols.mrp.credentials = self.service.credentials
        self._has_paired = True

    @property
    def device_provides_pin(self):
        """Return True if remote device presents PIN code, else False."""
        return True

    def pin(self, pin):
        """Pin code used for pairing."""
        self.pin_code = str(pin).zfill(4)
        _LOGGER.debug("MRP PIN changed to %s", self.pin_code)
