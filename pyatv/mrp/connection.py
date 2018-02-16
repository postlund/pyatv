"""Network layer for MRP."""

import asyncio
import logging

from pyatv.log import log_binary
from pyatv.mrp import chacha20
from pyatv.mrp import protobuf
from pyatv.mrp.variant import (read_variant, write_variant)

_LOGGER = logging.getLogger(__name__)


class MrpConnection:
    """Network layer that encryptes/decryptes and (de)serializes messages."""

    def __init__(self, host, port, loop):
        """Initialize a new MrpConnection."""
        self.host = str(host)  # TODO: which datatype do I want here?
        self.port = port
        self.loop = loop
        self._buffer = b''
        self._reader = None
        self._writer = None
        self._chacha = None

    def enable_encryption(self, output_key, input_key):
        """Enable encryption with the specified keys."""
        self._chacha = chacha20.Chacha20Cipher(output_key, input_key)

    @property
    def connected(self):
        """If a connection is open or not."""
        return self._reader and self._writer

    @asyncio.coroutine
    def connect(self):
        """Connect to device."""
        self._reader, self._writer = yield from asyncio.open_connection(
            self.host, self.port, loop=self.loop)  # TODO: timeout

    def close(self):
        """Close connection to device."""
        if self._writer:
            self._writer.close()
        self._chacha = None

    def send(self, message):
        """Send message to device."""
        serialized = message.SerializeToString()

        log_binary(_LOGGER, '>> Send', Data=serialized)
        if self._chacha:
            serialized = self._chacha.encrypt(serialized)
            log_binary(_LOGGER, '>> Send', Encrypted=serialized)

        data = write_variant(len(serialized)) + serialized
        self._writer.write(data)
        _LOGGER.debug('>> Send: Protobuf=%s', message)

    @asyncio.coroutine
    def receive(self):
        """Receive message from device."""
        data = yield from self._reader.read(1024)
        if data == b'':
            _LOGGER.debug('Device closed the connection')
            # TODO: other exception
            raise Exception('device closed the connection')

        # A message might be split over several reads, so we store a buffer and
        # try to decode messages from that buffer
        self._buffer += data
        log_binary(_LOGGER, '<< Receive', Data=data)

        # The variant tells us how much data must follow
        length, raw = read_variant(self._buffer)
        if len(raw) < length:
            _LOGGER.debug(
                'Require %d bytes but only %d in buffer', length, len(raw))
            return None

        data = raw[:length]  # Incoming message (might be encrypted)
        self._buffer = raw[length:]  # Buffer, might contain more messages

        if self._chacha:
            data = self._chacha.decrypt(data)
            log_binary(_LOGGER, '<< Receive', Decrypted=data)

        parsed = protobuf.ProtocolMessage()
        parsed.ParseFromString(data)
        _LOGGER.debug('<< Receive: Protobuf=%s', parsed)
        return parsed
