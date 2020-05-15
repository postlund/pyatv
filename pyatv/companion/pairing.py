"""Device pairing and derivation of encryption keys."""

import logging

from pyatv.const import Protocol
from pyatv.interface import PairingHandler

_LOGGER = logging.getLogger(__name__)


class CompanionPairingHandler(PairingHandler):
    """Pairing handler used to pair the Companion link protocol."""

    def __init__(self, config, session, loop):
        """Initialize a new CompanionPairingHandler."""
        super().__init__(session, config.get_service(Protocol.Companion))
        self.pin_code = None

    async def close(self):
        """Call to free allocated resources after pairing."""
        await super().close()

    @property
    def has_paired(self):
        """If a successful pairing has been performed."""
        return False

    async def begin(self):
        """Start pairing process."""
        _LOGGER.debug("Start pairing Companion")

    async def finish(self):
        """Stop pairing process."""
        _LOGGER.debug("Finish pairing Companion")

    @property
    def device_provides_pin(self):
        """Return True if remote device presents PIN code, else False."""
        return True

    def pin(self, pin):
        """Pin code used for pairing."""
        self.pin_code = str(pin).zfill(4)
        _LOGGER.debug("Companion PIN changed to %s", self.pin_code)
