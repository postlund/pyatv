"""Device pairing and derivation of encryption keys."""
import logging
from typing import Optional, cast

from pyatv.auth.hap_pairing import PairSetupProcedure
from pyatv.core import AbstractPairingHandler
from pyatv.interface import BaseConfig, BaseService
from pyatv.protocols.airplay.auth import AuthenticationType, pair_setup
from pyatv.protocols.airplay.utils import AirPlayFlags, parse_features
from pyatv.support.http import ClientSessionManager, HttpConnection, http_connect

_LOGGER = logging.getLogger(__name__)


def get_preferred_auth_type(service: BaseService) -> AuthenticationType:
    """Return the preferred authentication type depending on what is supported."""
    features_string = service.properties.get("features")
    if features_string:
        features = parse_features(features_string)
        if AirPlayFlags.SupportsCoreUtilsPairingAndEncryption in features:
            return AuthenticationType.HAP
    return AuthenticationType.Legacy


class AirPlayPairingHandler(AbstractPairingHandler):
    """Base class for API used to pair with an Apple TV."""

    def __init__(
        self,
        config: BaseConfig,
        service: BaseService,
        session_manager: ClientSessionManager,
        auth_type: AuthenticationType,
        **kwargs
    ) -> None:
        """Initialize a new MrpPairingHandler."""
        super().__init__(session_manager, service, device_provides_pin=True)
        self.auth_type = auth_type
        self.http: Optional[HttpConnection] = None
        self.address: str = str(config.address)
        self.pairing_procedure: Optional[PairSetupProcedure] = None

    async def close(self) -> None:
        """Call to free allocated resources after pairing."""
        await super().close()
        if self.http:
            self.http.close()
            self.http = None

    async def _pair_begin(self) -> None:
        """Start pairing process."""
        self.http = await http_connect(self.address, self.service.port)
        self.pairing_procedure = pair_setup(self.auth_type, self.http)
        await self.pairing_procedure.start_pairing()

    async def _pair_finish(self) -> str:
        """Stop pairing process."""
        # Can never be None here
        procedure = cast(PairSetupProcedure, self.pairing_procedure)
        return str(await procedure.finish_pairing("", int(self._pin or "0000")))
