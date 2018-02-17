"""Implementation of the MRP protocol."""

import uuid
import asyncio
import logging

from collections import namedtuple

from pyatv.mrp import (messages, protobuf)
from pyatv.mrp.pairing import MrpPairingVerifier
from pyatv.mrp.srp import Credentials

_LOGGER = logging.getLogger(__name__)

Listener = namedtuple('Listener', 'func data')
OutstandingMessage = namedtuple('OutstandingMessage', 'semaphore response')


# pylint: disable=too-many-instance-attributes
class MrpProtocol(object):
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
        self._one_shots = {}
        self._initial_message_sent = False

    def add_listener(self, listener, message_type, data=None, one_shot=False):
        """Add a listener that will receice incoming messages."""
        lst = self._one_shots if one_shot else self._listeners

        if message_type not in lst:
            lst[message_type] = []

        lst[message_type].append(Listener(listener, data))

    # TODO: This method is too big for its own good. Must split and clean up.
    @asyncio.coroutine
    def start(self):
        """Connect to device and listen to incoming messages."""
        if self.connection.connected:
            return

        yield from self.connection.connect()

        # In case credentials have been given externally (i.e. not by pairing
        # with a device), then use that client id
        if self.service.device_credentials:
            self.srp.pairing_id = Credentials.parse(
                self.service.device_credentials).client_id

        # The first message must always be DEVICE_INFORMATION, otherwise the
        # device will not respond with anything
        msg = messages.device_information(
            'pyatv', self.srp.pairing_id.decode())
        yield from self.send_and_receive(msg)
        self._initial_message_sent = True

        # This should be the first message sent after encryption has
        # been enabled
        yield from self.send(messages.set_connection_state())

        @asyncio.coroutine
        def _wait_for_updates(_, semaphore):
            # Use a counter here whenever more than one message is expected
            semaphore.release()

        # Wait for some stuff to arrive before returning
        semaphore = asyncio.Semaphore(value=0, loop=self.loop)
        self.add_listener(_wait_for_updates,
                          protobuf.SET_STATE_MESSAGE,
                          data=semaphore,
                          one_shot=False)

        # Subscribe to updates at this stage
        yield from self.send(messages.client_updates_config())
        yield from self.send(messages.wake_device())

        try:
            yield from asyncio.wait_for(
                semaphore.acquire(), 1, loop=self.loop)
        except asyncio.TimeoutError:
            # This is not an issue itself, but I should do something better.
            # Basically this gives the device about one second to respond with
            # some metadata before continuing.
            pass

    def stop(self):
        """Disconnect from device."""
        if self._outstanding:
            _LOGGER.warning('There were %d outstanding requests',
                            len(self._outstanding))

        self._initial_message_sent = False
        self._outstanding = {}
        self.connection.close()

    @asyncio.coroutine
    def _connect_and_encrypt(self):
        if not self.connection.connected:
            yield from self.start()

        # Encryption can be enabled whenever credentials are available but only
        # after DEVICE_INFORMATION has been sent
        if self.service.device_credentials and self._initial_message_sent:
            self._initial_message_sent = False

            # Verify credentials and generate keys
            credentials = Credentials.parse(self.service.device_credentials)
            pair_verifier = MrpPairingVerifier(self, self.srp, credentials)

            yield from pair_verifier.verify_credentials()
            output_key, input_key = pair_verifier.encryption_keys()
            self.connection.enable_encryption(output_key, input_key)

    @asyncio.coroutine
    def send(self, message):
        """Send a message and expect no response."""
        yield from self._connect_and_encrypt()
        self.connection.send(message)

    @asyncio.coroutine
    def send_and_receive(self, message, generate_identifier=True, timeout=5):
        """Send a message and wait for a response."""
        yield from self._connect_and_encrypt()

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
        return (yield from self._receive(identifier, timeout))

    @asyncio.coroutine
    def _receive(self, identifier, timeout):
        semaphore = asyncio.Semaphore(value=0, loop=self.loop)
        self._outstanding[identifier] = OutstandingMessage(semaphore, None)

        try:
            # The connection instance will dispatch the message
            yield from asyncio.wait_for(
                semaphore.acquire(), timeout, loop=self.loop)

        except:
            del self._outstanding[identifier]
            raise

        response = self._outstanding[identifier].response
        del self._outstanding[identifier]
        return response

    def message_received(self, message):
        """Message was received from device."""
        _LOGGER.debug('Received message: %s', message)

        if message.identifier:
            identifier = message.identifier
        else:
            identifier = 'type_' + str(message.type)

        # If the message identifer is outstanding, then someone is
        # waiting for the respone so we save it here
        if identifier in self._outstanding:
            outstanding = OutstandingMessage(
                self._outstanding[identifier].semaphore, message)
            self._outstanding[identifier] = outstanding
            self._outstanding[identifier].semaphore.release()
        else:
            try:
                self.loop.call_soon(self._dispatch, message)
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception('failed to dispatch')

    # TODO: dispatching should maybe not be a coroutine?
    @asyncio.coroutine
    def _dispatch(self, message):
        for listener in self._listeners.get(message.type, []):
            _LOGGER.debug('Dispatching message with type %d (%s)',
                          message.type, type(message.inner()).__name__)
            yield from listener.func(message, listener.data)

        if message.type in self._one_shots:
            for one_shot in self._one_shots.get(message.type,):
                _LOGGER.debug('One-shot with message type %d', message.type)
                yield from one_shot.func(message, one_shot.data)

            del self._one_shots[message.type]
