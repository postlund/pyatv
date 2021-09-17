"""Network layer for MRP."""

from abc import abstractmethod
import asyncio
import logging

from pyatv import exceptions
from pyatv.protocols.mrp import protobuf
from pyatv.support import chacha20, log_binary, log_protobuf
from pyatv.support.net import tcp_keepalive
from pyatv.support.state_producer import StateProducer
from pyatv.support.variant import read_variant, write_variant

_LOGGER = logging.getLogger(__name__)


class AbstractMrpConnection(asyncio.Protocol, StateProducer):
    """Abstract base class for an MRP connection."""

    @abstractmethod
    async def connect(self) -> None:
        """Connect to device."""

    @property
    @abstractmethod
    def connected(self) -> bool:
        """If a connection is open or not."""

    @abstractmethod
    def close(self) -> None:
        """Close connection to device."""

    @abstractmethod
    def send(self, message: protobuf.ProtocolMessage) -> None:
        """Send protobuf message to device."""


class MrpConnection(
    AbstractMrpConnection
):  # pylint: disable=too-many-instance-attributes  # noqa
    """Network layer that encryptes/decryptes and (de)serializes messages."""

    def __init__(self, host, port, loop, atv=None):
        """Initialize a new MrpConnection."""
        super().__init__()
        self.host = str(host)
        self.port = port
        self.atv = atv
        self.loop = loop
        self._log_str = ""
        self._buffer = b""
        self._chacha = None
        self._transport = None

    def connection_made(self, transport):
        """Device connection was made."""
        _LOGGER.debug("Connection made to device")
        self._transport = transport
        sock = transport.get_extra_info("socket")
        try:
            tcp_keepalive(sock)
        except exceptions.NotSupportedError as ex:
            _LOGGER.warning("Keep-alive not supported: %s", str(ex))

        dstaddr, dstport = sock.getpeername()
        srcaddr, srcport = sock.getsockname()
        self._log_str = f"{srcaddr}:{srcport}<->{dstaddr}:{dstport} "
        _LOGGER.debug("%s Connection established", self._log_str)

    def connection_lost(self, exc):
        """Device connection was dropped."""
        _LOGGER.debug("%s Disconnected from device: %s", self._log_str, exc)
        self._transport = None
        self.listener.stop()  # pylint: disable=no-member

        if self.atv:
            if exc is None:
                self.atv.listener.connection_closed()
            else:
                self.atv.listener.connection_lost(exc)

    def eof_received(self):
        """Device sent EOF (no more data)."""
        _LOGGER.debug("%s Received EOF from server", self._log_str)
        if self._transport.can_write_eof():
            self._transport.write_eof()
        self._transport.close()

    def enable_encryption(self, output_key, input_key):
        """Enable encryption with the specified keys."""
        self._chacha = chacha20.Chacha20Cipher(output_key, input_key)

    @property
    def connected(self) -> bool:
        """If a connection is open or not."""
        return self._transport is not None

    async def connect(self) -> None:
        """Connect to device."""
        await self.loop.create_connection(lambda: self, self.host, self.port)

    def close(self) -> None:
        """Close connection to device."""
        _LOGGER.debug("%s Closing connection", self._log_str)
        if self._transport:
            self._transport.close()
        self._transport = None
        self._chacha = None

    def send(self, message: protobuf.ProtocolMessage) -> None:
        """Send protobuf message to device."""
        serialized = message.SerializeToString()

        log_binary(_LOGGER, self._log_str + ">> Send", Data=serialized)
        if self._chacha:
            serialized = self._chacha.encrypt(serialized)
            log_binary(_LOGGER, self._log_str + ">> Send", Encrypted=serialized)

        data = write_variant(len(serialized)) + serialized
        self._transport.write(data)
        log_protobuf(_LOGGER, self._log_str + ">> Send: Protobuf", message)

    def send_raw(self, data):
        """Send message to device."""
        log_binary(_LOGGER, self._log_str + ">> Send raw", Data=data)
        if self._chacha:
            data = self._chacha.encrypt(data)
            log_binary(_LOGGER, self._log_str + ">> Send raw", Encrypted=data)

        data = write_variant(len(data)) + data
        self._transport.write(data)

    def data_received(self, data):
        """Message was received from device."""
        # A message might be split over several reads, so we store a buffer and
        # try to decode messages from that buffer
        self._buffer += data
        log_binary(_LOGGER, self._log_str + "<< Receive", Data=data)

        while self._buffer:
            # The variant tells us how much data must follow
            length, raw = read_variant(self._buffer)
            if len(raw) < length:
                _LOGGER.debug(
                    "%s Require %d bytes but only %d in buffer",
                    self._log_str,
                    length,
                    len(raw),
                )
                break

            data = raw[:length]  # Incoming message (might be encrypted)
            self._buffer = raw[length:]  # Buffer, might contain more messages

            try:
                self._handle_message(data)
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("%s Failed to handle message", self._log_str)

    def _handle_message(self, data):
        if self._chacha:
            data = self._chacha.decrypt(data)
            log_binary(_LOGGER, self._log_str + "<< Receive", Decrypted=data)

        parsed = protobuf.ProtocolMessage()
        parsed.ParseFromString(data)
        log_protobuf(_LOGGER, self._log_str + "<< Receive: Protobuf", parsed)

        self.listener.message_received(parsed, data)  # pylint: disable=no-member

    def __str__(self):
        """Return string representation of connection object."""
        return f"MRP:{self.host}"
