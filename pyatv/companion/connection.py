"""Connection abstraction for Companion protocol."""
from abc import ABC
import asyncio
from collections import deque
from enum import Enum
import logging
from typing import Optional, Tuple

from pyatv import exceptions
from pyatv.support import chacha20, log_binary

_LOGGER = logging.getLogger(__name__)

AUTH_TAG_LENGTH = 16
HEADER_LENGTH = 4


# pylint: disable=invalid-name
class FrameType(Enum):
    """Frame type values."""

    Unknown = 0
    NoOp = 1
    PS_Start = 3
    PS_Next = 4
    PV_Start = 5
    PV_Next = 6
    U_OPACK = 7
    E_OPACK = 8
    P_OPACK = 9
    PA_Req = 10
    PA_Rsp = 11
    SessionStartRequest = 16
    SessionStartResponse = 17
    SessionData = 18
    FamilyIdentityRequest = 32
    FamilyIdentityResponse = 33
    FamilyIdentityUpdate = 34


#  pylint: enable=invalid-name


class CompanionConnectionListener(ABC):
    """Listener interface for a Companion connection."""

    def disconnected(self) -> None:
        """Disconnect from companion device."""


class CompanionConnection(asyncio.Protocol):
    """Remote connection to a Companion device."""

    def __init__(
        self,
        loop: asyncio.AbstractEventLoop,
        host: str,
        port: int,
        listener: Optional[CompanionConnectionListener] = None,
    ) -> None:
        """Initialize a new CompanionConnection instance."""
        self.loop = loop
        self.host = host
        self.port = port
        self.listener: Optional[CompanionConnectionListener] = listener
        self.transport = None
        self._buffer: bytes = b""
        self._chacha: Optional[chacha20.Chacha20Cipher] = None
        self._queue: deque = deque()

    @property
    def connected(self) -> bool:
        """If a connection is open or not."""
        return self.transport is not None

    async def connect(self) -> None:
        """Connect to device."""
        await self.loop.create_connection(lambda: self, self.host, self.port)

    def close(self) -> None:
        """Close connection to device."""
        _LOGGER.debug("Closing connection")
        if self.transport:
            self.transport.close()
            self.transport = None

    def enable_encryption(self, output_key: bytes, input_key: bytes) -> None:
        """Enable encryption with the specified keys."""
        self._chacha = chacha20.Chacha20Cipher(output_key, input_key, nonce_length=12)

    async def exchange(
        self, frame_type: FrameType, data: bytes, timeout: int
    ) -> Tuple[bytes, bytes]:
        """Send message and wait for response."""
        semaphore = asyncio.Semaphore(value=0)
        self._queue.append([None, frame_type, data, semaphore])

        if len(self._queue) == 1:
            self._send_first_in_queue()

        try:
            await asyncio.wait_for(semaphore.acquire(), timeout)
        except Exception:
            # Note here: This will break if the response is just late, not sure how to
            # deal with that as there are no identifier in the message that can be used
            # to match response
            self._queue.popleft()
            self._send_first_in_queue()
            raise

        response = self._queue.popleft()[0]
        log_binary(_LOGGER, "Recv data", Data=response)

        header, data = response[0:4], response[4:]

        if self._chacha:
            data = self._chacha.decrypt(data, aad=header)
            log_binary(_LOGGER, "<< Receive data", Header=header, Decrypted=data)

        # If anyone has a pending request, make sure to send it
        self._send_first_in_queue()

        return header, data

    def _send_first_in_queue(self) -> None:
        if self.transport is None:
            raise exceptions.InvalidStateError("not connected")

        if not self._queue:
            return

        _, frame_type, data, _ = self._queue[0]

        log_binary(
            _LOGGER, ">> Send data", FrameType=bytes([frame_type.value]), Data=data
        )

        payload_length = len(data) + (AUTH_TAG_LENGTH if self._chacha else 0)
        header = bytes([frame_type.value]) + payload_length.to_bytes(3, byteorder="big")

        if self._chacha:
            data = self._chacha.encrypt(data, aad=header)
            log_binary(_LOGGER, ">> Send", Header=header, Encrypted=data)

        self.transport.write(header + data)

    def connection_made(self, transport):
        """Handle that connection was eatablished."""
        _LOGGER.debug("Connected to companion device %s:%d", self.host, self.port)
        self.transport = transport

    def data_received(self, data):
        """Handle data received from companion."""
        self._buffer += data
        log_binary(_LOGGER, "Received data", Data=data)

        payload_length = HEADER_LENGTH + int.from_bytes(data[1:4], byteorder="big")
        if len(self._buffer) < payload_length:
            _LOGGER.debug(
                "Require %d bytes but only %d in buffer",
                len(self._buffer),
                payload_length,
            )
            return

        data = self._buffer[0:payload_length]
        self._buffer = self._buffer[payload_length:]

        if self._queue:
            receiver = self._queue[0]
            receiver[0] = data
            receiver[3].release()
        else:
            log_binary(_LOGGER, "Received data with not receiver", Data=data)

    @staticmethod
    def error_received(exc):
        """Error received from companion."""
        _LOGGER.debug("Connection error: %s", exc)

    def connection_lost(self, exc):
        """Handle that connection was lost from companion."""
        _LOGGER.debug("Connection lost to remote device: %s", exc)
        self.transport = None
        if self.listener:
            self.listener.disconnected()
            self.listener = None
