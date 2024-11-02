"""Connection abstraction for Companion protocol."""

from abc import ABC
import asyncio
from collections import deque
from enum import Enum
import logging
from typing import Optional

from pyatv import exceptions
from pyatv.support import chacha20, log_binary
from pyatv.support.state_producer import StateProducer

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

    def frame_received(self, frame_type: FrameType, data: bytes) -> None:
        """Frame was received from remote device."""


class CompanionConnection(asyncio.Protocol):
    """Remote connection to a Companion device."""

    def __init__(
        self,
        loop: asyncio.AbstractEventLoop,
        host: str,
        port: int,
        device_listener: Optional[StateProducer] = None,
    ) -> None:
        """Initialize a new CompanionConnection instance."""
        self.loop = loop
        self.host = host
        self.port = port
        self._listener: Optional[CompanionConnectionListener] = None
        self._device_listener = device_listener
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

    def set_listener(self, listener: CompanionConnectionListener) -> None:
        """Set the CompanionConnectionListener in a way that doesn't break pylint."""
        self._listener = listener

    def send(self, frame_type: FrameType, data: bytes) -> None:
        """Send message without waiting for a response."""
        if self.transport is None:
            raise exceptions.InvalidStateError("not connected")

        payload_length = len(data)
        if self._chacha and payload_length > 0:
            payload_length += AUTH_TAG_LENGTH
        header = bytes([frame_type.value]) + payload_length.to_bytes(3, byteorder="big")

        log_binary(
            _LOGGER,
            ">> Send data",
            FrameType=bytes([frame_type.value]),
            Data=data,
        )

        if self._chacha and len(data) > 0:
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

        while len(self._buffer) >= HEADER_LENGTH:
            payload_length = HEADER_LENGTH + int.from_bytes(
                self._buffer[1:HEADER_LENGTH], byteorder="big"
            )
            if len(self._buffer) < payload_length:
                _LOGGER.debug(
                    "Require %d bytes but only %d in buffer",
                    payload_length,
                    len(self._buffer),
                )
                break

            header = self._buffer[0:HEADER_LENGTH]
            payload = self._buffer[HEADER_LENGTH:payload_length]
            self._buffer = self._buffer[payload_length:]

            try:
                if self._chacha and len(payload) > 0:
                    payload = self._chacha.decrypt(payload, aad=header)

                self._listener.frame_received(FrameType(header[0]), payload)
            except Exception:
                _LOGGER.exception("failed to handle frame")

    @staticmethod
    def error_received(exc):
        """Error received from companion."""
        _LOGGER.debug("Connection error: %s", exc)

    def connection_lost(self, exc):
        """Handle that connection was lost from companion."""
        _LOGGER.debug("Connection lost to remote device: %s", exc)
        self.transport = None
        if self._device_listener is not None:
            if exc:
                self._device_listener.listener.connection_lost(exc)
            else:
                self._device_listener.listener.connection_closed()
