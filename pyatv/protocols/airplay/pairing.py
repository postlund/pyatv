"""Device pairing and derivation of encryption keys."""

import logging
from typing import Optional

from pyatv import exceptions
from pyatv.auth.hap_pairing import PairSetupProcedure
from pyatv.const import Protocol
from pyatv.core import Core
from pyatv.interface import PairingHandler
from pyatv.protocols.airplay.auth import AuthenticationType, pair_setup
from pyatv.protocols.airplay.utils import AirPlayMajorVersion
from pyatv.support import error_handler
from pyatv.support.http import HttpConnection, http_connect

_LOGGER = logging.getLogger(__name__)


class AirPlayPairingHandler(PairingHandler):
    """Base class for API used to pair with an Apple TV."""

    def __init__(
        self, core: Core, airplay_version: AirPlayMajorVersion, **kwargs
    ) -> None:
        """Initialize a new MrpPairingHandler."""
        super().__init__(core.session_manager, core.service)
        self._name: str = kwargs.get("name", core.settings.info.name)
        self.airplay_version = airplay_version
        self.http: Optional[HttpConnection] = None
        self.address: str = str(core.config.address)
        self.pairing_procedure: Optional[PairSetupProcedure] = None
        self.pin_code: Optional[str] = None
        self._has_paired: bool = False
        self._settings = core.settings

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
        self.http = await http_connect(self.address, self.service.port)
        self.pairing_procedure = pair_setup(
            (
                AuthenticationType.HAP
                if self.airplay_version == AirPlayMajorVersion.AirPlayV2
                else AuthenticationType.Legacy
            ),
            self.http,
        )
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
                "",
                self.pin_code,
                self._name,
            )
        )

        # HACK: This pairing handler is shared between AirPlay and RAOP, so we need to
        #       check which protocol we are pairing before storing the credentials.
        if self.service.protocol == Protocol.AirPlay:
            self._settings.protocols.airplay.credentials = self.service.credentials
        else:
            self._settings.protocols.raop.credentials = self.service.credentials

        self._has_paired = True

    def pin(self, pin: int) -> None:
        """Pin code used for pairing."""
        self.pin_code = str(pin).zfill(4)
        _LOGGER.debug("AirPlay PIN changed to %s", self.pin_code)

    @property
    def device_provides_pin(self) -> bool:
        """Return True if remote device presents PIN code, else False."""
        return True
