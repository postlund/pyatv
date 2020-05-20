"""Implementation of the Companion protocol."""

import asyncio
import logging

from pyatv import exceptions
from pyatv.companion.auth import CompanionPairingVerifier
from pyatv.companion.srp import Credentials

_LOGGER = logging.getLogger(__name__)


class CompanionProtocol:
    """Protocol logic related to Companion."""

    def __init__(self, connection, srp, service):
        """Initialize a new CompanionProtocol."""
        self.connection = connection
        self.connection.listener = self
        self.srp = srp
        self.service = service
        self.has_verified = False  # TODO: Hack

    async def start(self, skip_initial_messages=False):
        """Connect to device and listen to incoming messages."""
        if self.connection.connected:
            return

        await self.connection.connect()

        if self.service.credentials:
            self.srp.pairing_id = Credentials.parse(self.service.credentials).client_id

        _LOGGER.debug("Companion credentials: %s", self.service.credentials)

        await self._connect_and_encrypt()

    def stop(self):
        """Disconnect from device."""
        self.connection.close()

    async def _connect_and_encrypt(self):
        if not self.connection.connected:
            await self.start()

        # Verify credentials and generate keys
        if self.service.credentials and not self.has_verified:
            self.has_verified = True
            credentials = Credentials.parse(self.service.credentials)
            pair_verifier = CompanionPairingVerifier(self, self.srp, credentials)

            try:
                await pair_verifier.verify_credentials()
                output_key, input_key = pair_verifier.encryption_keys()
                self.connection.enable_encryption(output_key, input_key)
            except Exception as ex:
                raise exceptions.AuthenticationError(str(ex)) from ex

    async def send_and_receive(self, message, timeout=5):
        """Send a message and wait for a response."""
        await self._connect_and_encrypt()
        self.connection.send(message)
        return await self.connection.read()
