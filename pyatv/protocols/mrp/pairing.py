"""Device pairing and derivation of encryption keys."""

import asyncio
import logging

from pyatv.auth.hap_pairing import HapCredentials
from pyatv.auth.hap_srp import SRPAuthHandler
from pyatv.core import AbstractPairingHandler
from pyatv.interface import BaseConfig, BaseService
from pyatv.protocols.mrp.auth import MrpPairSetupProcedure, MrpPairVerifyProcedure
from pyatv.protocols.mrp.connection import MrpConnection
from pyatv.protocols.mrp.protocol import MrpProtocol
from pyatv.support.http import ClientSessionManager

_LOGGER = logging.getLogger(__name__)


class MrpPairingHandler(AbstractPairingHandler):
    """Base class for API used to pair with an Apple TV."""

    def __init__(
        self,
        config: BaseConfig,
        service: BaseService,
        session_manager: ClientSessionManager,
        loop: asyncio.AbstractEventLoop,
        **kwargs
    ) -> None:
        """Initialize a new MrpPairingHandler."""
        super().__init__(session_manager, service, device_provides_pin=True)
        self.connection = MrpConnection(config.address, self.service.port, loop)
        self.srp = SRPAuthHandler()
        self.protocol = MrpProtocol(self.connection, self.srp, self.service)
        self.pairing_procedure = MrpPairSetupProcedure(self.protocol, self.srp)

    async def close(self) -> None:
        """Call to free allocated resources after pairing."""
        self.connection.close()
        await super().close()

    async def _pair_begin(self) -> None:
        """Start pairing process."""
        await self.pairing_procedure.start_pairing()

    async def _pair_finish(self) -> str:
        """Stop pairing process."""
        credentials: HapCredentials = await self.pairing_procedure.finish_pairing(
            "", int(self._pin or "0000")
        )

        _LOGGER.debug("Verifying credentials %s", credentials)

        verifier = MrpPairVerifyProcedure(self.protocol, self.srp, credentials)
        await verifier.verify_credentials()

        return str(credentials)
