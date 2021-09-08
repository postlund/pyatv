"""Implementation of the MRP protocol."""

import asyncio
from collections import namedtuple
from enum import Enum
import logging
import uuid

from pyatv import exceptions
from pyatv.auth.hap_pairing import parse_credentials
from pyatv.core.protocol import heartbeater
from pyatv.protocols.mrp import messages, protobuf
from pyatv.protocols.mrp.auth import MrpPairVerifyProcedure

_LOGGER = logging.getLogger(__name__)

HEARTBEAT_INTERVAL = 30
HEARTBEAT_RETRIES = 1  # One regular attempt + retries

SRP_SALT = "MediaRemote-Salt"
SRP_OUTPUT_INFO = "MediaRemote-Write-Encryption-Key"
SRP_INPUT_INFO = "MediaRemote-Read-Encryption-Key"

Listener = namedtuple("Listener", "func data")
OutstandingMessage = namedtuple("OutstandingMessage", "semaphore response")


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
class MrpProtocol:
    """Protocol logic related to MRP.

    This class wraps an MrpConnection instance and will automatically:
    * Connect whenever it is needed
    * Send necessary messages automatically, e.g. DEVICE_INFORMATION
    * Enable encryption at the right time

    It provides an API for sending and receiving messages.
    """

    def __init__(self, connection, srp, service):
        """Initialize a new MrpProtocol."""
        self.connection = connection
        self.connection.listener = self
        self.srp = srp
        self.service = service
        self.device_info = None
        self._heartbeat_task = None
        self._outstanding = {}
        self._listeners = {}
        self._state = ProtocolState.NOT_CONNECTED

    def add_listener(self, listener, message_type, data=None):
        """Add a listener that will receice incoming messages."""
        if message_type not in self._listeners:
            self._listeners[message_type] = []

        self._listeners[message_type].append(Listener(listener, data))

    async def start(self, skip_initial_messages=False):
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
            msg = messages.device_information("pyatv", self.srp.pairing_id.decode())

            self.device_info = await self.send_and_receive(msg)

            # This is a hack to support re-use of a protocol object in
            # proxy (will be removed/refactored later)
            if skip_initial_messages:
                return

            await self._enable_encryption()

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
        else:
            # We're now ready
            self._state = ProtocolState.READY

    def stop(self):
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
        self._heartbeat_task = asyncio.ensure_future(
            heartbeater(
                name=str(self.connection),
                sender_func=self.send_and_receive,
                failure_func=lambda exc: self.connection.close,
                message_factory=lambda: messages.create(protobuf.GENERIC_MESSAGE),
            )
        )

    async def _enable_encryption(self):
        # Encryption can be enabled whenever credentials are available but only
        # after DEVICE_INFORMATION has been sent
        if self.service.credentials is None:
            return

        # Verify credentials and generate keys
        credentials = parse_credentials(self.service.credentials)
        pair_verifier = MrpPairVerifyProcedure(self, self.srp, credentials)

        try:
            await pair_verifier.verify_credentials()
            output_key, input_key = pair_verifier.encryption_keys(
                SRP_SALT, SRP_OUTPUT_INFO, SRP_INPUT_INFO
            )
            self.connection.enable_encryption(output_key, input_key)
        except Exception as ex:
            raise exceptions.AuthenticationError(str(ex)) from ex

    async def send(self, message):
        """Send a message and expect no response."""
        if self._state not in [
            ProtocolState.CONNECTED,
            ProtocolState.READY,
        ]:
            raise exceptions.InvalidStateError(self._state.name)

        self.connection.send(message)

    async def send_and_receive(self, message, generate_identifier=True, timeout=5):
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

    async def _receive(self, identifier, timeout):
        semaphore = asyncio.Semaphore(value=0)
        self._outstanding[identifier] = OutstandingMessage(semaphore, None)

        try:
            # The connection instance will dispatch the message
            await asyncio.wait_for(semaphore.acquire(), timeout)

        except:  # noqa
            del self._outstanding[identifier]
            raise

        response = self._outstanding[identifier].response
        del self._outstanding[identifier]
        return response

    def message_received(self, message, _):
        """Message was received from device."""
        # If the message identifier is outstanding, then someone is
        # waiting for the respone so we save it here
        identifier = message.identifier or "type_" + str(message.type)
        if identifier in self._outstanding:
            outstanding = OutstandingMessage(
                self._outstanding[identifier].semaphore, message
            )
            self._outstanding[identifier] = outstanding
            self._outstanding[identifier].semaphore.release()
        else:
            self._dispatch(message)

    def _dispatch(self, message):
        async def _call_listener(func):
            # Make sure to catch any exceptions caused by the listener so we don't get
            # unfished tasks laying around
            try:
                await func
            except asyncio.CancelledError:
                pass
            except Exception:
                _LOGGER.exception("error during dispatch")

        for listener in self._listeners.get(message.type, []):
            _LOGGER.debug(
                "Dispatching message with type %d (%s) to %s",
                message.type,
                type(message.inner()).__name__,
                listener,
            )
            asyncio.ensure_future(_call_listener(listener.func(message, listener.data)))
