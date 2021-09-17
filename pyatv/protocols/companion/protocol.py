"""Implementation of the Companion protocol."""

import logging
from typing import Dict

from pyatv import exceptions
from pyatv.auth.hap_pairing import parse_credentials
from pyatv.auth.hap_srp import SRPAuthHandler
from pyatv.interface import BaseService
from pyatv.protocols.companion import opack
from pyatv.protocols.companion.auth import CompanionPairVerifyProcedure
from pyatv.protocols.companion.connection import CompanionConnection, FrameType

_LOGGER = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 5  # Seconds

SRP_SALT = ""
SRP_OUTPUT_INFO = "ClientEncrypt-main"
SRP_INPUT_INFO = "ServerEncrypt-main"


class CompanionProtocol:
    """Protocol logic related to Companion."""

    def __init__(
        self,
        connection: CompanionConnection,
        srp: SRPAuthHandler,
        service: BaseService,
    ):
        """Initialize a new CompanionProtocol."""
        self.connection = connection
        self.srp = srp
        self.service = service
        self._chacha = None
        self._is_started = False

    async def start(self):
        """Connect to device and listen to incoming messages."""
        if self._is_started:
            raise exceptions.ProtocolError("Already started")

        self._is_started = True
        await self.connection.connect()

        if self.service.credentials:
            self.srp.pairing_id = parse_credentials(self.service.credentials).client_id

        _LOGGER.debug("Companion credentials: %s", self.service.credentials)

        await self._setup_encryption()

    def stop(self):
        """Disconnect from device."""
        self.connection.close()

    async def _setup_encryption(self):
        if self.service.credentials:
            credentials = parse_credentials(self.service.credentials)
            pair_verifier = CompanionPairVerifyProcedure(self, self.srp, credentials)

            try:
                await pair_verifier.verify_credentials()
                output_key, input_key = pair_verifier.encryption_keys(
                    SRP_SALT, SRP_OUTPUT_INFO, SRP_INPUT_INFO
                )
                self.connection.enable_encryption(output_key, input_key)
            except Exception as ex:
                raise exceptions.AuthenticationError(str(ex)) from ex

    async def exchange_opack(
        self, frame_type: FrameType, data: object, timeout: int = DEFAULT_TIMEOUT
    ) -> Dict[str, object]:
        """Send data as OPACK and decode result as OPACK."""
        _LOGGER.debug("Send OPACK: %s", data)
        _, payload = await self.connection.exchange(
            frame_type, opack.pack(data), timeout
        )
        unpacked_object, _ = opack.unpack(payload)
        _LOGGER.debug("Receive OPACK: %s", unpacked_object)

        if not isinstance(unpacked_object, dict):
            raise exceptions.ProtocolError(
                f"Received unexpected type: {type(unpacked_object)}"
            )

        if "_em" in unpacked_object:
            raise exceptions.ProtocolError(f"Command failed: {unpacked_object['_em']}")

        return unpacked_object
