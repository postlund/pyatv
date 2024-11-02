"""Logic related to logical AirPlay channels.

This module only deals with AirPlay 2 related channels right now.
"""

from abc import ABC
import logging
from random import randrange
from typing import Any, List, NamedTuple, Optional, Tuple

from pyatv.auth.hap_channel import AbstractHAPChannel
from pyatv.protocols.airplay.utils import decode_plist_body, encode_plist_body
from pyatv.protocols.mrp import protobuf
from pyatv.support.http import (
    HttpRequest,
    HttpResponse,
    format_request,
    format_response,
    parse_request,
    parse_response,
)
from pyatv.support.packet import defpacket
from pyatv.support.variant import read_variant, write_variant

_LOGGER = logging.getLogger(__name__)

DATA_HEADER_PADDING = 0x00000000

DataHeader = defpacket(
    "DataFrame", size="I", message_type="12s", command="4s", seqno="Q", padding="I"
)


class BaseEventChannel(AbstractHAPChannel, ABC):
    """Base class for connection used to handle the event channel."""

    @staticmethod
    def format_request(request: HttpRequest) -> bytes:
        """Encode event channel request."""
        return format_request(request)

    @staticmethod
    def parse_request(data: bytes) -> Tuple[Optional[HttpRequest], bytes, bytes]:
        """Parse event channel request."""
        request, rest = parse_request(data)
        return request, data[: len(data) - len(rest)], rest

    @staticmethod
    def format_response(response: HttpResponse) -> bytes:
        """Encode event channel response."""
        return format_response(response)

    @staticmethod
    def parse_response(data: bytes) -> Tuple[Optional[HttpResponse], bytes, bytes]:
        """Parse event channel response."""
        response, rest = parse_response(data)
        return response, data[: len(data) - len(rest)], rest


class EventChannel(BaseEventChannel):
    """Connection used to handle the event channel."""

    def handle_received(self) -> None:
        """Handle received data that was put in buffer."""
        self.buffer: bytes
        while self.buffer:
            try:
                request, _, self.buffer = self.parse_request(self.buffer)
                if request is None:
                    _LOGGER.debug("Not enough data to parse request on event channel")
                    break

                _LOGGER.debug("Got message on event channel: %s", request)

                # Send a positive response to satisfy the other end of the channel
                headers = {
                    "Content-Length": "0",
                    "Audio-Latency": "0",
                }
                if "Server" in request.headers:
                    headers["Server"] = request.headers["Server"]
                if "CSeq" in request.headers:
                    headers["CSeq"] = request.headers["CSeq"]
                self.send(
                    self.format_response(
                        HttpResponse(
                            request.protocol,
                            request.version,
                            200,
                            "OK",
                            headers,
                            b"",
                        )
                    )
                )
            except Exception:
                _LOGGER.exception("Failed to handle message on event channel")


class DataStreamListener(ABC):
    """Listener interface for DataStreamChannel."""

    def handle_protobuf(self, message: protobuf.ProtocolMessage) -> None:
        """Handle incoming protobuf message."""

    def handle_connection_lost(self, exc: Optional[Exception]) -> None:
        """Device connection was dropped."""


class DataStreamMessage(NamedTuple):
    """Data stream channel message."""

    message_type: bytes
    command: bytes
    seqno: int
    padding: int
    payload: bytes


class BaseDataStreamChannel(AbstractHAPChannel, ABC):
    """Base class for connection used to handle the data stream channel."""

    @staticmethod
    def encode_message(message: DataStreamMessage) -> bytes:
        """Encode data stream channel message."""
        return (
            DataHeader.encode(
                DataHeader.length + len(message.payload),
                message.message_type,
                message.command,
                message.seqno,
                message.padding,
            )
            + message.payload
        )

    @staticmethod
    def encode_payload(payload: Any) -> bytes:
        """Encode message payload."""
        return encode_plist_body(payload)

    @staticmethod
    def encode_protobufs(protobuf_messages: List[protobuf.ProtocolMessage]) -> bytes:
        """Encode protobuf messages."""
        serialized_messages = []
        for protobuf_message in protobuf_messages:
            serialized_message = protobuf_message.SerializeToString()
            serialized_length = write_variant(len(serialized_message))
            serialized_messages.append(serialized_length)
            serialized_messages.append(serialized_message)
        return b"".join(serialized_messages)

    def encode_reply(self, seqno: int) -> bytes:
        """Encode data stream channel reply."""
        return self.encode_message(
            DataStreamMessage(
                b"rply" + 8 * b"\x00",
                4 * b"\x00",
                seqno,
                DATA_HEADER_PADDING,
                b"",
            )
        )

    @staticmethod
    def decode_message(data: bytes) -> Tuple[Optional[DataStreamMessage], bytes, bytes]:
        """Decode data stream channel message."""
        if len(data) < DataHeader.length:
            return None, b"", data
        header = DataHeader.decode(data, allow_excessive=True)
        if len(data) < header.size:
            _LOGGER.debug(
                "Not enough data on data channel (has %d, expects %d)",
                len(data),
                header.size,
            )
            return None, b"", data
        return (
            DataStreamMessage(
                header.message_type,
                header.command,
                header.seqno,
                header.padding,
                data[DataHeader.length : header.size],
            ),
            data[: header.size],
            data[header.size :],
        )

    @staticmethod
    def decode_payload(payload: bytes) -> Any:
        """Decode message payload."""
        data = decode_plist_body(payload)
        if data is None:
            _LOGGER.warning("failed to process data frame")
        return data

    @staticmethod
    def decode_protobufs(data: bytes) -> List[protobuf.ProtocolMessage]:
        """Decode protobuf messages."""
        pb_messages = []
        try:
            while data:
                # Protobuf fields are encoded in ascending numerical order and
                # every message must include type (field #1), which is encoded
                # with the tag 0x08. This is not a valid length since the
                # minimal message length is at least 40 (type and
                # uniqueIdentifier). We can use this to detect cases where the
                # message is not length prefixed, which is known to happen for
                # ConfigureConnectionMessage.
                if data[0] == 0x8:
                    message, data = data, b""
                else:
                    length, raw = read_variant(data)
                    if len(raw) < length:
                        _LOGGER.warning("Expected %d bytes, got %d", length, len(raw))
                        break
                    message, data = raw[:length], raw[length:]

                assert message[0] == 0x8
                pb_msg = protobuf.ProtocolMessage()
                pb_msg.ParseFromString(message)
                pb_messages.append(pb_msg)
        except Exception:
            _LOGGER.exception("failed to process data frame")
        return pb_messages


class DataStreamChannel(BaseDataStreamChannel):
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
            message, _, self.buffer = self.decode_message(self.buffer)
            if not message:
                break

            payload = self.decode_payload(message.payload)
            if payload:
                self._process_payload(payload)

            # If this was a request, send a reply to satisfy other end
            if message.message_type.startswith(b"sync"):
                self.send(self.encode_reply(message.seqno))

    def _process_payload(self, message) -> None:
        data = message.get("params", {}).get("data")
        if data is None:
            _LOGGER.debug("Got message with unsupported format: %s", message)
            return

        for pb_msg in self.decode_protobufs(data):
            self.listener.handle_protobuf(pb_msg)

    def send_protobuf(self, message: protobuf.ProtocolMessage) -> None:
        """Serialize a protobuf message and send it to receiver."""
        self.send(
            self.encode_message(
                DataStreamMessage(
                    b"sync" + 8 * b"\x00",
                    b"comm",
                    self.send_seqno,
                    DATA_HEADER_PADDING,
                    self.encode_payload(
                        {"params": {"data": self.encode_protobufs([message])}}
                    ),
                )
            )
        )
