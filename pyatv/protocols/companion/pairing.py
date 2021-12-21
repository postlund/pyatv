"""Device pairing and derivation of encryption keys."""
import asyncio
import logging

from pyatv.auth.hap_srp import SRPAuthHandler
from pyatv.core import AbstractPairingHandler
from pyatv.interface import BaseConfig, BaseService
from pyatv.protocols.companion.auth import CompanionPairSetupProcedure
from pyatv.protocols.companion.connection import CompanionConnection
from pyatv.protocols.companion.protocol import CompanionProtocol
from pyatv.support.http import ClientSessionManager

_LOGGER = logging.getLogger(__name__)


class CompanionPairingHandler(AbstractPairingHandler):
    """Pairing handler used to pair the Companion link protocol."""

    def __init__(
        self,
        config: BaseConfig,
        service: BaseService,
        session: ClientSessionManager,
        loop: asyncio.AbstractEventLoop,
        **kwargs
    ):
        """Initialize a new CompanionPairingHandler."""
        super().__init__(session, service, device_provides_pin=True)
        self.connection = CompanionConnection(
            loop, str(config.address), self.service.port, None
        )
        self.srp = SRPAuthHandler()
        self.protocol = CompanionProtocol(self.connection, self.srp, self.service)
        self.pairing_procedure = CompanionPairSetupProcedure(self.protocol, self.srp)

    async def close(self) -> None:
        """Call to free allocated resources after pairing."""
        self.protocol.stop()
        await super().close()

    async def _pair_begin(self) -> None:
        """Start pairing process."""
        await self.pairing_procedure.start_pairing()

    async def _pair_finish(self) -> str:
        """Stop pairing process."""
        return await self.pairing_procedure.finish_pairing("", int(self._pin or "0000"))
