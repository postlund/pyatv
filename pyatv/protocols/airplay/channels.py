"""Logic related to logical AirPlay channels.

This module only deals with AirPlay 2 related channels right now.
"""
from abc import ABC
import logging
import plistlib
from random import randrange
from typing import Optional

from pyatv.auth.hap_channel import AbstractHAPChannel
from pyatv.protocols.mrp import protobuf
from pyatv.support.http import parse_request
from pyatv.support.packet import defpacket
from pyatv.support.variant import read_variant, write_variant

_LOGGER = logging.getLogger(__name__)

DATA_HEADER_PADDING = 0x00000000

DataHeader = defpacket(
    "DataFrame", size="I", message_type="12s", command="4s", seqno="Q", padding="I"
)


class EventChannel(AbstractHAPChannel):
    """Connection used to handle the event channel."""

    def handle_received(self) -> None:
        """Handle received data that was put in buffer."""
        self.buffer: bytes
        while self.buffer:
            try:
                request, self.buffer = parse_request(self.buffer)
                if request is None:
                    _LOGGER.debug("Not enough data to parse request on event channel")
                    break

                _LOGGER.debug("Got message on event channel: %s", request)

                # Send a positive response to satisfy the other end of the channel
                # TODO: Add public method to pyatv.http to format a message
                headers = {
                    "Content-Length": 0,
                    "Audio-Latency": 0,
                    "Server": request.headers.get("Server"),
                    "CSeq": request.headers.get("CSeq"),
                }
                response = (
                    f"{request.protocol}/{request.version} 200 OK\r\n"
                    + "\r\n".join(f"{key}: {value}" for key, value in headers.items())
                    + "\r\n\r\n"
                )
                self.send(response.encode("utf-8"))
            except Exception:
                _LOGGER.exception("Failed to handle message on event channel")


class DataStreamListener(ABC):
    """Listener interface for DataStreamChannel."""

    def handle_protobuf(self, message: protobuf.ProtocolMessage) -> None:
        """Handle incoming protobuf message."""

    def handle_connection_lost(self, exc: Optional[Exception]) -> None:
        """Device connection was dropped."""


class DataStreamChannel(AbstractHAPChannel):
    """Connection used to handle the data stream channel."""

    def __init__(self, output_key: bytes, input_key: bytes) -> None:
        """Initialize a new DataStreamChannel instance."""
        super().__init__(output_key, input_key)
        self.send_seqno = randrange(0x100000000, 0x1FFFFFFFF)

    def connection_lost(self, exc: Optional[Exception]) -> None:
        """Device connection was dropped."""
        self.listener.handle_connection_lost(exc)

    def handle_received(self) -> None:
        """Handle received data that was put in buffer."""
        self.buffer: bytes
        while len(self.buffer) >= DataHeader.length:
            header = DataHeader.decode(self.buffer, allow_excessive=True)
            if len(self.buffer) < header.size:
                _LOGGER.debug(
                    "Not enough data on data channel (has %d, expects %d)",
                    len(self.buffer),
                    header.size,
                )
                break

            try:
                self._process_message_from_buffer(header)
            except Exception:
                _LOGGER.exception("failed to process data frame")

            self.buffer = self.buffer[header.size :]

    def _process_message_from_buffer(self, header) -> None:
        # Decode payload and process it
        payload = plistlib.loads(self.buffer[DataHeader.length : header.size])
        if payload:
            self._process_payload(payload)

        # If this was a request, send a reply to satisfy other end
        if header.message_type.startswith(b"sync"):
            self.send(
                DataHeader.encode(
                    DataHeader.length,
                    b"rply" + 8 * b"\x00",
                    4 * b"\x00",
                    header.seqno,
                    DATA_HEADER_PADDING,
                )
            )

    def _process_payload(self, message) -> None:
        data = message.get("params", {}).get("data")
        if data is None:
            _LOGGER.debug("Got message with unsupported format: %s", message)
            return

        while data:
            length, raw = read_variant(data)
            if len(raw) < length:
                _LOGGER.warning("Expected %d bytes, got %d", length, len(raw))
                return

            message = raw[:length]
            data = raw[length:]

            pb_msg = protobuf.ProtocolMessage()
            pb_msg.ParseFromString(message)
            self.listener.handle_protobuf(pb_msg)

    def send_protobuf(self, message: protobuf.ProtocolMessage) -> None:
        """Serialize a protobuf message and send it to receiver."""
        serialized_message = message.SerializeToString()
        serialized_length = write_variant(len(serialized_message))

        payload = plistlib.dumps(
            {"params": {"data": serialized_length + serialized_message}},
            fmt=plistlib.FMT_BINARY,  # pylint: disable=no-member
        )

        self.send(
            DataHeader.encode(
                DataHeader.length + len(payload),
                b"sync" + 8 * b"\x00",
                b"comm",
                self.send_seqno,
                DATA_HEADER_PADDING,
            )
            + payload
        )
