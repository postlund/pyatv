"""Device pairing and derivation of encryption keys."""
import logging
from typing import Optional

from pyatv import exceptions
from pyatv.auth.hap_pairing import PairSetupProcedure
from pyatv.interface import BaseConfig, BaseService, PairingHandler
from pyatv.protocols.airplay.auth import AuthenticationType, pair_setup
from pyatv.protocols.airplay.utils import AirPlayFlags, parse_features
from pyatv.support import error_handler
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


class AirPlayPairingHandler(PairingHandler):
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
        super().__init__(session_manager, service)
        self.auth_type = auth_type
        self.http: Optional[HttpConnection] = None
        self.address: str = str(config.address)
        self.pairing_procedure: Optional[PairSetupProcedure] = None
        self.pin_code: Optional[str] = None
        self._has_paired: bool = False

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
        self.pairing_procedure = pair_setup(self.auth_type, self.http)
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
            )
        )
        self._has_paired = True

    def pin(self, pin: int) -> None:
        """Pin code used for pairing."""
        self.pin_code = str(pin).zfill(4)
        _LOGGER.debug("AirPlay PIN changed to %s", self.pin_code)

    @property
    def device_provides_pin(self) -> bool:
        """Return True if remote device presents PIN code, else False."""
        return True
