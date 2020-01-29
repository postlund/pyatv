"""Device pairing and derivation of encryption keys."""

import logging

from pyatv import exceptions
from pyatv.const import Protocol
from pyatv.interface import PairingHandler
from pyatv.mrp.auth import MrpPairingProcedure
from pyatv.mrp.srp import SRPAuthHandler
from pyatv.mrp.protocol import MrpProtocol
from pyatv.mrp.connection import MrpConnection
from pyatv.support import error_handler

_LOGGER = logging.getLogger(__name__)


class MrpPairingHandler(PairingHandler):
    """Base class for API used to pair with an Apple TV."""

    def __init__(self, config, session, loop):
        """Initialize a new MrpPairingHandler."""
        super().__init__(session, config.get_service(Protocol.MRP))
        self.connection = MrpConnection(
            config.address, self.service.port, loop)
        self.srp = SRPAuthHandler()
        self.protocol = MrpProtocol(
            loop, self.connection, self.srp, self.service)
        self.pairing_procedure = MrpPairingProcedure(
            self.protocol, self.srp)
        self.pin_code = None

    async def close(self):
        """Call to free allocated resources after pairing."""
        self.connection.close()
        await super().close()

    @property
    def has_paired(self):
        """If a successful pairing has been performed."""
        return self.service.credentials is not None

    def begin(self):
        """Start pairing process."""
        return error_handler(self.pairing_procedure.start_pairing,
                             exceptions.PairingError)

    async def finish(self):
        """Stop pairing process."""
        if not self.pin_code:
            raise exceptions.PairingError('no pin given')

        self.service.credentials = str(await error_handler(
            self.pairing_procedure.finish_pairing,
            exceptions.PairingError,
            self.pin_code))

    @property
    def device_provides_pin(self):
        """Return True if remote device presents PIN code, else False."""
        return True

    def pin(self, pin):
        """Pin code used for pairing."""
        self.pin_code = str(pin).zfill(4)
