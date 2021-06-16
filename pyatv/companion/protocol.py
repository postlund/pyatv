"""Implementation of the Companion protocol."""

import logging
from typing import Dict

from pyatv import exceptions
from pyatv.companion import opack
from pyatv.companion.auth import CompanionPairingVerifier
from pyatv.companion.connection import CompanionConnection, FrameType
from pyatv.conf import CompanionService
from pyatv.support.hap_srp import HapCredentials, SRPAuthHandler

_LOGGER = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 5  # Seconds


class CompanionProtocol:
    """Protocol logic related to Companion."""

    def __init__(
        self,
        connection: CompanionConnection,
        srp: SRPAuthHandler,
        service: CompanionService,
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
            self.srp.pairing_id = HapCredentials.parse(
                self.service.credentials
            ).client_id

        _LOGGER.debug("Companion credentials: %s", self.service.credentials)

        await self._setup_encryption()

    def stop(self):
        """Disconnect from device."""
        self.connection.close()

    async def _setup_encryption(self):
        if self.service.credentials:
            credentials = HapCredentials.parse(self.service.credentials)
            pair_verifier = CompanionPairingVerifier(self, self.srp, credentials)

            try:
                await pair_verifier.verify_credentials()
                output_key, input_key = pair_verifier.encryption_keys()
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

        return unpacked_object
