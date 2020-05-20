"""Connection abstraction for Companion protocol."""
import asyncio
import logging

from pyatv.mrp import chacha20
from pyatv.support import log_binary

_LOGGER = logging.getLogger(__name__)


# TODO: Temporary solution for a connection
class CompanionConnection(asyncio.Protocol):
    """Remote connection to a Companion device."""

    def __init__(self, loop, host, port):
        """Initialize a new CompanionConnection instance."""
        self.loop = loop
        self.host = str(host)
        self.port = port
        self.transport = None
        self.semaphore = asyncio.Semaphore(value=0)
        self.buffer = b""
        self._chacha = None

    @property
    def connected(self):
        """If a connection is open or not."""
        return self.transport is not None

    async def connect(self):
        """Connect to device."""
        _LOGGER.debug("Connecting to Companion client")
        await self.loop.create_connection(lambda: self, self.host, self.port)

    def enable_encryption(self, output_key, input_key):
        """Enable encryption with the specified keys."""
        self._chacha = chacha20.Chacha20Cipher(output_key, input_key)

    def close(self):
        """Close connection to device."""
        _LOGGER.debug("Closing connection")
        if self.transport:
            self.transport.close()
        self.transport = None
        self._chacha = None

    def send(self, data):
        """Send data to companion."""
        log_binary(_LOGGER, "Send data", Data=data)
        if self._chacha:
            serialized = self._chacha.encrypt(data)
            log_binary(_LOGGER, ">> Send", Encrypted=serialized)
        self.transport.write(data)

    async def read(self):
        """Wait for data to be available and return it."""
        await asyncio.wait_for(
            self.semaphore.acquire(),
            timeout=3,
        )
        buffer = self.buffer
        header = self.buffer[0:4]
        data = self.buffer[4:]
        if self._chacha:
            data = self._chacha.decrypt(data)
            log_binary(_LOGGER, "<< Receive", Decrypted=data)

        self.buffer = b""
        return header + data

    def connection_made(self, transport):
        """Handle that connection was eatablished."""
        _LOGGER.debug("Connected to companion device")
        self.transport = transport

    def data_received(self, data):
        """Handle data received from companion."""
        log_binary(_LOGGER, "Received data", Data=data)
        self.buffer += data
        self.semaphore.release()

    def error_received(self, exc):
        """Error received from companion."""
        _LOGGER.debug("Error: %s", exc)

    def connection_lost(self, exc):
        """Handle that connection was lost from companion."""
        _LOGGER.debug("Connection lost: %s", exc)
