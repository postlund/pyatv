"""Implementation of the MRP protocol."""

import asyncio
import uuid
import logging

from collections import namedtuple

from pyatv import exceptions
from pyatv.mrp import messages
from pyatv.mrp.auth import MrpPairingVerifier
from pyatv.mrp.srp import Credentials

_LOGGER = logging.getLogger(__name__)

Listener = namedtuple('Listener', 'func data')
OutstandingMessage = namedtuple('OutstandingMessage', 'semaphore response')


# pylint: disable=too-many-instance-attributes
class MrpProtocol:
    """Protocol logic related to MRP.

    This class wraps an MrpConnection instance and will automatically:
    * Connect whenever it is needed
    * Send necessary messages automatically, e.g. DEVICE_INFORMATION
    * Enable encryption at the right time

    It provides an API for sending and receiving messages.
    """

    def __init__(self, loop, connection, srp, service):
        """Initialize a new MrpProtocol."""
        self.loop = loop
        self.connection = connection
        self.connection.listener = self
        self.srp = srp
        self.service = service
        self._outstanding = {}
        self._listeners = {}
        self._initial_message_sent = False

    def add_listener(self, listener, message_type, data=None):
        """Add a listener that will receice incoming messages."""
        if message_type not in self._listeners:
            self._listeners[message_type] = []

        self._listeners[message_type].append(Listener(listener, data))

    async def start(self, skip_initial_messages=False):
        """Connect to device and listen to incoming messages."""
        if self.connection.connected:
            return

        await self.connection.connect()

        # In case credentials have been given externally (i.e. not by pairing
        # with a device), then use that client id
        if self.service.credentials:
            self.srp.pairing_id = Credentials.parse(
                self.service.credentials).client_id

        # The first message must always be DEVICE_INFORMATION, otherwise the
        # device will not respond with anything
        msg = messages.device_information(
            'pyatv', self.srp.pairing_id.decode())

        await self.send_and_receive(msg)
        self._initial_message_sent = True

        # This is a hack to support re-use of a protocol object in
        # proxy (will be removed/refactored later)
        if skip_initial_messages:
            return

        await self._connect_and_encrypt()

        # This should be the first message sent after encryption has
        # been enabled
        await self.send(messages.set_connection_state())

        # Subscribe to updates at this stage
        await self.send(messages.client_updates_config())
        await self.send_and_receive(messages.get_keyboard_session())

    def stop(self):
        """Disconnect from device."""
        if self._outstanding:
            _LOGGER.warning('There were %d outstanding requests',
                            len(self._outstanding))

        self._initial_message_sent = False
        self._outstanding = {}
        self.connection.close()

    async def _connect_and_encrypt(self):
        if not self.connection.connected:
            await self.start()

        # Encryption can be enabled whenever credentials are available but only
        # after DEVICE_INFORMATION has been sent
        if self.service.credentials and self._initial_message_sent:
            self._initial_message_sent = False

            # Verify credentials and generate keys
            credentials = Credentials.parse(self.service.credentials)
            pair_verifier = MrpPairingVerifier(self, self.srp, credentials)

            try:
                await pair_verifier.verify_credentials()
                output_key, input_key = pair_verifier.encryption_keys()
                self.connection.enable_encryption(output_key, input_key)
            except Exception as ex:
                raise exceptions.AuthenticationError(str(ex)) from ex

    async def send(self, message):
        """Send a message and expect no response."""
        await self._connect_and_encrypt()
        self.connection.send(message)

    async def send_and_receive(self, message,
                               generate_identifier=True, timeout=5):
        """Send a message and wait for a response."""
        await self._connect_and_encrypt()

        # Some messages will respond with the same identifier as used in the
        # corresponding request. Others will not and one example is the crypto
        # message (for pairing). They will never include an identifer, but it
        # it is in turn only possible to have one of those message outstanding
        # at one time (i.e. it's not possible to mix up the responses). In
        # those cases, a "fake" identifier is used that includes the message
        # type instead.
        if generate_identifier:
            identifier = str(uuid.uuid4())
            message.identifier = identifier
        else:
            identifier = 'type_' + str(message.type)

        self.connection.send(message)
        return await self._receive(identifier, timeout)

    async def _receive(self, identifier, timeout):
        semaphore = asyncio.Semaphore(value=0, loop=self.loop)
        self._outstanding[identifier] = OutstandingMessage(semaphore, None)

        try:
            # The connection instance will dispatch the message
            await asyncio.wait_for(
                semaphore.acquire(), timeout, loop=self.loop)

        except:  # noqa
            del self._outstanding[identifier]
            raise

        response = self._outstanding[identifier].response
        del self._outstanding[identifier]
        return response

    def message_received(self, message, _):
        """Message was received from device."""
        # If the message identifer is outstanding, then someone is
        # waiting for the respone so we save it here
        identifier = message.identifier or 'type_' + str(message.type)
        if identifier in self._outstanding:
            outstanding = OutstandingMessage(
                self._outstanding[identifier].semaphore, message)
            self._outstanding[identifier] = outstanding
            self._outstanding[identifier].semaphore.release()
        else:
            self._dispatch(message)

    def _dispatch(self, message):
        for listener in self._listeners.get(message.type, []):
            _LOGGER.debug('Dispatching message with type %d (%s) to %s',
                          message.type,
                          type(message.inner()).__name__,
                          listener)
            asyncio.ensure_future(
                listener.func(message, listener.data), loop=self.loop)
