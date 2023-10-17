"""Implementation of the MRP protocol."""

import asyncio
from collections import namedtuple
from enum import Enum
import logging
from typing import Dict, NamedTuple, Optional
import uuid

import async_timeout

from pyatv import exceptions
from pyatv.auth.hap_pairing import parse_credentials
from pyatv.auth.hap_srp import SRPAuthHandler
from pyatv.core.protocol import MessageDispatcher, heartbeater
from pyatv.interface import BaseService
from pyatv.protocols.mrp import messages, protobuf
from pyatv.protocols.mrp.auth import MrpPairVerifyProcedure
from pyatv.protocols.mrp.connection import AbstractMrpConnection
from pyatv.settings import InfoSettings
from pyatv.support import error_handler

_LOGGER = logging.getLogger(__name__)

HEARTBEAT_INTERVAL = 30
HEARTBEAT_RETRIES = 1  # One regular attempt + retries

SRP_SALT = "MediaRemote-Salt"
SRP_OUTPUT_INFO = "MediaRemote-Write-Encryption-Key"
SRP_INPUT_INFO = "MediaRemote-Read-Encryption-Key"

Listener = namedtuple("Listener", "func data")


class OutstandingMessage(NamedTuple):
    """Sent message waiting for response."""

    semaphore: asyncio.Semaphore
    response: protobuf.ProtocolMessage


class ProtocolState(Enum):
    """Protocol internal state."""

    NOT_CONNECTED = 0
    """Protocol state is not connected."""

    CONNECTING = 1
    """Protocol state is connecting."""

    CONNECTED = 2
    """Protocol state is connected."""

    READY = 3
    """Protocol state is ready."""

    STOPPED = 4
    """Protocol state is stopped."""


async def heartbeat_loop(protocol):
    """Periodically send heartbeat messages to device."""
    _LOGGER.debug("Starting heartbeat loop")
    count = 0
    attempts = 0
    message = messages.create(protobuf.GENERIC_MESSAGE)
    while True:
        try:
            # Re-attempts are made with no initial delay to more quickly
            # recover a failed heartbeat (if possible)
            if attempts == 0:
                await asyncio.sleep(HEARTBEAT_INTERVAL)

            _LOGGER.debug("Sending periodic heartbeat %d", count)
            await protocol.send_and_receive(message)
            _LOGGER.debug("Got heartbeat %d", count)
        except asyncio.CancelledError:
            break
        except Exception:
            attempts += 1
            if attempts > HEARTBEAT_RETRIES:
                _LOGGER.error("heartbeat %d failed after %d tries", count, attempts)
                protocol.connection.close()
                break
            _LOGGER.debug("heartbeat %d failed", count)
        else:
            attempts = 0
        finally:
            count += 1

    _LOGGER.debug("Stopping heartbeat loop at %d", count)


# pylint: disable=too-many-instance-attributes
class MrpProtocol(MessageDispatcher[int, protobuf.ProtocolMessage]):
    """Protocol logic related to MRP.

    This class wraps an MrpConnection instance and will automatically:
    * Connect whenever it is needed
    * Send necessary messages automatically, e.g. DEVICE_INFORMATION
    * Enable encryption at the right time

    It provides an API for sending and receiving messages.
    """

    def __init__(
        self,
        connection: AbstractMrpConnection,
        srp: SRPAuthHandler,
        service: BaseService,
        info: InfoSettings,
    ) -> None:
        """Initialize a new MrpProtocol."""
        super().__init__()
        self.connection = connection
        self.connection.listener = self
        self.srp = srp
        self.service = service
        self.info = info
        self.device_info: Optional[protobuf.ProtocolMessage] = None
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._outstanding: Dict[str, OutstandingMessage] = {}
        self._state: ProtocolState = ProtocolState.NOT_CONNECTED

    async def start(self, skip_initial_messages: bool = False) -> None:
        """Connect to device and listen to incoming messages."""
        if self._state != ProtocolState.NOT_CONNECTED:
            raise exceptions.InvalidStateError(self._state.name)

        self._state = ProtocolState.CONNECTING

        try:
            await self.connection.connect()

            self._state = ProtocolState.CONNECTED

            # In case credentials have been given externally (i.e. not by pairing
            # with a device), then use that client id
            if self.service.credentials:
                self.srp.pairing_id = parse_credentials(
                    self.service.credentials
                ).client_id

            # The first message must always be DEVICE_INFORMATION, otherwise the
            # device will not respond with anything
            self.device_info = await self.send_and_receive(
                messages.device_information(self.info, self.srp.pairing_id.decode())
            )

            # Distribute the device information to all listeners (as the
            # send_and_receive will stop that propagation).
            self.dispatch(protobuf.DEVICE_INFO_MESSAGE, self.device_info)

            # This is a hack to support reuse of a protocol object in
            # proxy (will be removed/refactored later)
            if skip_initial_messages:
                return

            await error_handler(self._enable_encryption, exceptions.AuthenticationError)

            # This should be the first message sent after encryption has
            # been enabled
            await self.send(messages.set_connection_state())

            # Subscribe to updates at this stage
            await self.send_and_receive(messages.client_updates_config())
            await self.send_and_receive(messages.get_keyboard_session())
        except Exception:
            # Something went wrong, let's do cleanup
            self.stop()
            raise

        # We're now ready
        self._state = ProtocolState.READY

    def stop(self) -> None:
        """Disconnect from device."""
        if self._outstanding:
            _LOGGER.warning(
                "There were %d outstanding requests", len(self._outstanding)
            )

        if self._heartbeat_task is not None:
            self._heartbeat_task.cancel()
            self._heartbeat_task = None
        self._outstanding = {}
        self.connection.close()
        self._state = ProtocolState.STOPPED

    def enable_heartbeat(self) -> None:
        """Enable sending periodic heartbeat messages."""

        async def _sender_func(message: Optional[protobuf.ProtocolMessage]) -> None:
            if message is not None:
                await self.send_and_receive(message)

        def _failure_func(exc: Exception):
            self.connection.close()

        self._heartbeat_task = asyncio.ensure_future(
            heartbeater(
                name=str(self.connection),
                sender_func=_sender_func,
                failure_func=_failure_func,
                message_factory=lambda: messages.create(protobuf.GENERIC_MESSAGE),
            )
        )

    async def _enable_encryption(self) -> None:
        # Encryption can be enabled whenever credentials are available but only
        # after DEVICE_INFORMATION has been sent
        if self.service.credentials is None:
            return

        # Verify credentials and generate keys
        credentials = parse_credentials(self.service.credentials)
        pair_verifier = MrpPairVerifyProcedure(self, self.srp, credentials)

        await pair_verifier.verify_credentials()
        output_key, input_key = pair_verifier.encryption_keys(
            SRP_SALT, SRP_OUTPUT_INFO, SRP_INPUT_INFO
        )
        self.connection.enable_encryption(output_key, input_key)

    async def send(self, message: protobuf.ProtocolMessage) -> None:
        """Send a message and expect no response."""
        if self._state not in [
            ProtocolState.CONNECTED,
            ProtocolState.READY,
        ]:
            raise exceptions.InvalidStateError(self._state.name)

        self.connection.send(message)

    async def send_and_receive(
        self,
        message: protobuf.ProtocolMessage,
        generate_identifier: bool = True,
        timeout: float = 5.0,
    ) -> protobuf.ProtocolMessage:
        """Send a message and wait for a response."""
        if self._state not in [
            ProtocolState.CONNECTED,
            ProtocolState.READY,
        ]:
            raise exceptions.InvalidStateError(self._state.name)

        # Some messages will respond with the same identifier as used in the
        # corresponding request. Others will not and one example is the crypto
        # message (for pairing). They will never include an identifier, but it
        # it is in turn only possible to have one of those message outstanding
        # at one time (i.e. it's not possible to mix up the responses). In
        # those cases, a "fake" identifier is used that includes the message
        # type instead.
        if generate_identifier:
            identifier = str(uuid.uuid4()).upper()
            message.identifier = identifier
        else:
            identifier = "type_" + str(message.type)

        self.connection.send(message)
        return await self._receive(identifier, timeout)

    async def _receive(
        self, identifier: str, timeout: float
    ) -> protobuf.ProtocolMessage:
        semaphore = asyncio.Semaphore(value=0)
        self._outstanding[identifier] = OutstandingMessage(
            semaphore, protobuf.ProtocolMessage()
        )

        try:
            # The connection instance will dispatch the message
            async with async_timeout.timeout(timeout):
                await semaphore.acquire()

        except Exception:
            del self._outstanding[identifier]
            raise

        response = self._outstanding[identifier].response
        del self._outstanding[identifier]
        return response

    def message_received(self, message: protobuf.ProtocolMessage, _) -> None:
        """Message was received from device."""
        # If the message identifier is outstanding, then someone is
        # waiting for the response so we save it here
        identifier = message.identifier or "type_" + str(message.type)
        if identifier in self._outstanding:
            outstanding = OutstandingMessage(
                self._outstanding[identifier].semaphore, message
            )
            self._outstanding[identifier] = outstanding
            self._outstanding[identifier].semaphore.release()
        else:
            self.dispatch(message.type, message)
