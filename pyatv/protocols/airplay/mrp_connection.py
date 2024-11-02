"""MRP connection implemented as a channel/stream over AirPlay."""

import logging
from typing import Optional

from pyatv import exceptions
from pyatv.protocols.airplay.ap2_session import AP2Session
from pyatv.protocols.airplay.channels import DataStreamChannel, DataStreamListener
from pyatv.protocols.mrp import protobuf
from pyatv.protocols.mrp.connection import AbstractMrpConnection
from pyatv.support import log_protobuf
from pyatv.support.state_producer import StateProducer

_LOGGER = logging.getLogger(__name__)


class AirPlayMrpConnection(AbstractMrpConnection, DataStreamListener):
    """Transparent connection/channel for transporting MRP messages."""

    def __init__(
        self, session: AP2Session, device_listener: Optional[StateProducer] = None
    ):
        """Initialize a new MrpConnection."""
        super().__init__()
        self.session = session
        self.data_channel: Optional[DataStreamChannel] = None
        self.device_listener = device_listener

    def connection_lost(self, exc: Optional[Exception]) -> None:
        """Device connection was dropped."""
        self.handle_connection_lost(exc)

    async def connect(self) -> None:
        """Connect to device."""
        if self.session.data_channel is None:
            raise exceptions.InvalidStateError("remote control channel not connected")

        self.data_channel = self.session.data_channel
        self.data_channel.listener = self

    def enable_encryption(self, output_key: bytes, input_key: bytes) -> None:
        """Enable encryption with the specified keys."""

    @property
    def connected(self) -> bool:
        """If a connection is open or not."""
        return True

    def close(self) -> None:
        """Close connection to device."""
        if self.data_channel is not None:
            _LOGGER.debug("Closing connection")
            self.data_channel.close()
            self.data_channel = None

    def send(self, message: protobuf.ProtocolMessage) -> None:
        """Send protobuf message to device."""
        if self.data_channel is not None:
            self.data_channel.send_protobuf(message)
            log_protobuf(_LOGGER, ">> Send: Protobuf", message)

    def handle_protobuf(self, message: protobuf.ProtocolMessage) -> None:
        """Handle incoming protobuf message."""
        log_protobuf(_LOGGER, "<< Receive: Protobuf", message)

        self.listener.message_received(message, None)  # pylint: disable=no-member

    def handle_connection_lost(self, exc: Optional[Exception]) -> None:
        """Device connection was dropped."""
        _LOGGER.debug("Disconnected from device: %s", exc)

        if self.device_listener:
            if exc is None:
                self.device_listener.listener.connection_closed()
            else:
                self.device_listener.listener.connection_lost(exc)
