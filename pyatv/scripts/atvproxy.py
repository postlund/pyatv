#!/usr/bin/env python3
"""Simple proxy server to intercept traffic."""

import argparse
import asyncio
from functools import partial
from ipaddress import IPv4Address
import logging
import plistlib
import sys
from typing import Any, Callable, Dict, Mapping, Optional, Union, cast

from google.protobuf.message import Message as ProtobufMessage
from zeroconf import Zeroconf

from pyatv.auth.hap_channel import AbstractHAPChannel, setup_channel
from pyatv.auth.hap_pairing import PairVerifyProcedure, parse_credentials
from pyatv.auth.hap_session import HAPSession
from pyatv.auth.hap_srp import SRPAuthHandler, hkdf_expand
from pyatv.const import Protocol
from pyatv.core import MutableService, mdns
from pyatv.protocols.airplay import extract_credentials, verify_connection
from pyatv.protocols.airplay.remote_control import (
    DATASTREAM_INPUT_INFO,
    DATASTREAM_OUTPUT_INFO,
    DATASTREAM_SALT,
    EVENTS_READ_INFO,
    EVENTS_SALT,
    EVENTS_WRITE_INFO,
)
from pyatv.protocols.airplay.server_auth import BaseAirPlayServerAuth
from pyatv.protocols.companion.connection import (
    AUTH_TAG_LENGTH,
    CompanionConnection,
    CompanionConnectionListener,
)
from pyatv.protocols.companion.protocol import (
    _AUTH_FRAMES,
    _OPACK_FRAMES,
    CompanionProtocol,
    FrameType,
    MessageType,
)
from pyatv.protocols.companion.server_auth import (
    SERVER_IDENTIFIER as COMPANION_SERVER_IDENTIFIER,
)
from pyatv.protocols.companion.server_auth import CompanionServerAuth
from pyatv.protocols.mrp import protobuf
from pyatv.protocols.mrp.connection import MrpConnection
from pyatv.protocols.mrp.protocol import MrpProtocol
from pyatv.protocols.mrp.server_auth import MrpServerAuth
from pyatv.protocols.mrp.server_auth import SERVER_IDENTIFIER as MRP_SERVER_IDENTIFIER
from pyatv.scripts import log_current_version
from pyatv.support import (
    chacha20,
    log_binary,
    net,
    opack,
    shift_hex_identifier,
    variant,
)
from pyatv.support.http import (
    BasicHttpServer,
    HttpConnection,
    HttpRequest,
    HttpResponse,
    http_connect,
)

_LOGGER = logging.getLogger(__name__)

DEVICE_NAME = "Proxy"
BLUETOOTH_ADDRESS = "DA:97:7C:BA:A3:7A"
AIRPLAY_IDENTIFIER = "4D797FD3-3538-427E-A47B-A32FC6CF3A6A"
MEDIA_REMOTE_ROUTE_IDENTIFIER = "DA4A238E-EE6C-4F5B-9691-4D0A8FC03532"

PROPERTY_CASE_MAP = {
    "rpad": "rpAD",
    "rpba": "rpBA",
    "rpfl": "rpFl",
    "rpha": "rpHA",
    "rphi": "rpHI",
    "rphn": "rpHN",
    "rpmac": "rpMac",
    "rpmd": "rpMd",
    "rpmrtid": "rpMRtID",
    "rpvr": "rpVr",
}
COMPANION_AUTH_FRAMES = [
    FrameType.PS_Start,
    FrameType.PS_Next,
    FrameType.PV_Start,
    FrameType.PV_Next,
]


class MrpAppleTVProxy(MrpServerAuth, asyncio.Protocol):
    """Implementation of a fake MRP Apple TV."""

    def __init__(self, loop, address, port, credentials):
        """Initialize a new instance of ProxyMrpAppleTV."""
        super().__init__(DEVICE_NAME)
        self.loop = loop
        self.buffer = b""
        self.transport = None
        self.chacha = None
        self.connection = MrpConnection(address, port, self.loop)
        self.protocol = MrpProtocol(
            self.connection,
            SRPAuthHandler(),
            MutableService(None, Protocol.MRP, port, {}, credentials=credentials),
        )

    async def start(self):
        """Start the proxy instance."""
        await self.protocol.start(skip_initial_messages=True)
        self.connection.listener = self
        self._process_buffer()

    def stop(self):
        """Stop the proxy instance."""
        if self.transport:
            self.transport.close()
            self.transport = None
        self.protocol.stop()

    def connection_made(self, transport):
        """Client did connect to proxy."""
        self.transport = transport

    def connection_lost(self, exc):
        """Handle that connection was lost to client."""
        _LOGGER.debug("Connection lost to client device: %s", exc)
        self.stop()

    def enable_encryption(self, output_key: bytes, input_key: bytes) -> None:
        """Enable encryption with specified keys."""
        self.chacha = chacha20.Chacha20Cipher(output_key, input_key)

    def send_to_client(self, message: ProtobufMessage):
        """Send protobuf message to client."""
        data = message.SerializeToString()
        _LOGGER.info("<<(DECRYPTED): %s", message)
        if self.chacha:
            data = self.chacha.encrypt(data)
            log_binary(_LOGGER, "<<(ENCRYPTED)", Message=message)

        length = variant.write_variant(len(data))
        self.transport.write(length + data)

    def send_raw(self, raw):
        """Send raw data to client."""
        parsed = protobuf.ProtocolMessage()
        parsed.ParseFromString(raw)

        log_binary(_LOGGER, "ATV->APP", Raw=raw)
        _LOGGER.info("ATV->APP Parsed: %s", parsed)
        if self.chacha:
            raw = self.chacha.encrypt(raw)
            log_binary(_LOGGER, "ATV->APP", Encrypted=raw)

        length = variant.write_variant(len(raw))
        try:
            self.transport.write(length + raw)
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Failed to send to app")

    def message_received(self, _, raw):
        """Message received from ATV."""
        self.send_raw(raw)

    def data_received(self, data):
        """Message received from iOS app/client."""
        self.buffer += data
        if self.connection.connected:
            self._process_buffer()

    def _process_buffer(self):
        while self.buffer:
            length, raw = variant.read_variant(self.buffer)
            if len(raw) < length:
                break

            data = raw[:length]
            self.buffer = raw[length:]
            if self.chacha:
                log_binary(_LOGGER, "ENC Phone->ATV", Encrypted=data)
                data = self.chacha.decrypt(data)

            message = protobuf.ProtocolMessage()
            message.ParseFromString(data)
            _LOGGER.info("(DEC Phone->ATV): %s", message)

            try:
                if message.type == protobuf.DEVICE_INFO_MESSAGE:
                    self.handle_device_info(message, message.inner())
                elif message.type == protobuf.CRYPTO_PAIRING_MESSAGE:
                    self.handle_crypto_pairing(message, message.inner())
                else:
                    self.connection.send_raw(data)
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Error while dispatching message")


class CompanionAppleTVProxy(
    CompanionServerAuth, CompanionConnectionListener, asyncio.Protocol
):
    """Implementation of a fake Companion device."""

    def __init__(
        self, loop: asyncio.AbstractEventLoop, address: str, port: int, credentials: str
    ) -> None:
        """Initialize a new instance of CompanionAppleTVProxy."""
        super().__init__(DEVICE_NAME)
        self.loop = loop
        self.buffer: bytes = b""
        self.credentials: str = credentials
        self.transport = None
        self.chacha: Optional[chacha20.Chacha20Cipher] = None
        self.connection: CompanionConnection = CompanionConnection(
            self.loop, address, port
        )
        self.protocol: CompanionProtocol = CompanionProtocol(
            self.connection,
            SRPAuthHandler(),
            MutableService(None, Protocol.Companion, port, {}, credentials=credentials),
        )
        # CompanionProtocol sets listener, override it now
        self.connection.set_listener(self)
        self.system_info_xid = None
        self._receive_event: asyncio.Event = asyncio.Event()
        self._receive_task: Optional[asyncio.Future] = None

    async def start(self) -> None:
        """Start the proxy instance."""
        await self.protocol.start()
        self._receive_task = asyncio.ensure_future(self._process_task())
        self._receive_event.set()

    def enable_encryption(self, output_key: bytes, input_key: bytes) -> None:
        """Enable encryption with the specified keys."""
        self.chacha = chacha20.Chacha20Cipher(output_key, input_key, nonce_length=12)

    async def _process_task(self) -> None:
        while True:
            _LOGGER.debug("Waiting for data from client")
            try:
                await self._receive_event.wait()
                await self._process_buffer()
            except asyncio.CancelledError:
                break
            except Exception:
                _LOGGER.exception("error processing incoming messages")

    async def _process_buffer(self) -> None:
        _LOGGER.debug("Process buffer (size: %d)", len(self.buffer))

        payload_length = 4 + int.from_bytes(self.buffer[1:4], byteorder="big")
        if len(self.buffer) < payload_length:
            _LOGGER.debug(
                "Expected %d bytes, have %d (waiting for more)",
                payload_length,
                len(self.buffer),
            )
            self._receive_event.clear()
            return

        frame_type = FrameType(self.buffer[0])
        data = self.buffer[4:payload_length]
        self.buffer = self.buffer[payload_length:]

        if frame_type in COMPANION_AUTH_FRAMES:
            try:
                self.handle_auth_frame(frame_type, opack.unpack(data)[0])
            except Exception:
                _LOGGER.exception("failed to handle auth frame")
        else:
            try:
                self.send_bytes_to_atv(frame_type, data)
            except Exception:
                _LOGGER.exception("data exchange failed")

    def connection_made(self, transport):
        """Client did connect to proxy."""
        _LOGGER.debug("Client connected to Companion proxy")
        self.transport = transport

    def connection_lost(self, exc):
        """Handle that connection was lost to client."""
        _LOGGER.debug("Connection lost to client device: %s", exc)
        if self.connection.connected:
            self.connection.close()
        if self._receive_task is not None:
            self._receive_task.cancel()

    def data_received(self, data):
        """Message received from client (iOS)."""
        log_binary(_LOGGER, "Data from client", Data=data)
        self.buffer += data
        if self.connection.connected:
            self._receive_event.set()

    def send_bytes_to_atv(self, frame_type: FrameType, data: bytes):
        """Send encoded data to remote device (ATV)."""
        log_binary(_LOGGER, f">>(ENCRYPTED) FrameType={frame_type}", Message=data)

        if self.chacha and len(data) > 0:
            header = bytes([frame_type.value]) + len(data).to_bytes(3, byteorder="big")
            data = self.chacha.decrypt(data, aad=header)
            log_binary(_LOGGER, "<<(DECRYPTED)", Message=data)

        if frame_type != FrameType.E_OPACK:
            self.connection.send(frame_type, data)
            return

        unpacked = cast(Dict[Any, Any], opack.unpack(data)[0])  # TODO: Bad cast
        self.process_outgoing_data(frame_type, unpacked)
        self.protocol.send_opack(frame_type, unpacked)

    def frame_received(self, frame_type: FrameType, data: bytes) -> None:
        """Frame was received from remote device."""
        if frame_type in _AUTH_FRAMES:
            # do not override authentication
            self.protocol.frame_received(frame_type, data)
            return

        _LOGGER.debug("Received frame %s: %s", frame_type, data)
        if frame_type in _OPACK_FRAMES:
            opack_data, _ = opack.unpack(data)
            _LOGGER.debug("Received OPACK: %s", opack_data)
            self.send_to_client(frame_type, opack_data)
        else:
            self.send_bytes_to_client(frame_type, data)

    def send_bytes_to_client(self, frame_type: FrameType, data: bytes) -> None:
        """Send encoded data to client device (iOS)."""
        if not self.transport:
            _LOGGER.error("Tried to send to client, but not connected")
            return

        payload_length = len(data)
        if self.chacha and payload_length > 0:
            payload_length += AUTH_TAG_LENGTH
        header = bytes([frame_type.value]) + payload_length.to_bytes(3, byteorder="big")

        if self.chacha and len(data) > 0:
            data = self.chacha.encrypt(data, aad=header)
            log_binary(_LOGGER, ">> Send", Header=header, Encrypted=data)

        self.transport.write(header + data)

    def send_to_client(self, frame_type: FrameType, data: object) -> None:
        """Send data to client device (iOS)."""
        self.process_incoming_data(frame_type, cast(Dict[str, Any], data))
        self.send_bytes_to_client(frame_type, opack.pack(data))

    def process_outgoing_data(self, frame_type: FrameType, data: Dict[str, Any]):
        """Apply any required modifications to outgoing data."""
        if frame_type != FrameType.E_OPACK:
            return

        data_type = data.get("_i")
        if data_type == "_systemInfo":
            self.system_info_xid = data.get("_x")
            creds = parse_credentials(self.credentials)
            payload = data["_c"]
            payload.update(
                {
                    # The server will drop older connections with the same
                    # identifier, so mangle them here to prevent disconnects if
                    # the client device is also directly connected to the
                    # server.
                    "_i": shift_hex_identifier(payload["_i"]),
                    "_idsID": creds.client_id.upper(),
                    "_pubID": shift_hex_identifier(payload["_pubID"]),
                }
            )

    def process_incoming_data(self, frame_type: FrameType, data: Dict[str, Any]):
        """Apply any required modifications to incoming data."""
        if frame_type != FrameType.E_OPACK:
            return

        message_type = data.get("_t")
        xid = data.get("_x")
        if message_type == MessageType.Response.value and xid == self.system_info_xid:
            self.system_info_xid = None
            payload = data["_c"]
            payload.update(
                {
                    "name": DEVICE_NAME,
                    "_i": "cafecafecafe",
                    "_idsID": COMPANION_SERVER_IDENTIFIER,
                    "_pubID": BLUETOOTH_ADDRESS,
                }
            )
            if "_mrID" in payload:
                payload["_mrID"] = MEDIA_REMOTE_ROUTE_IDENTIFIER
            if "_mRtID" in payload:
                payload["_mRtID"] = MEDIA_REMOTE_ROUTE_IDENTIFIER
            if "_siriInfo" in payload:
                siri_info = payload["_siriInfo"]
                if "peerData" in siri_info:
                    peer_data = siri_info["peerData"]
                    peer_data.update(
                        {
                            "userAssignedDeviceName": DEVICE_NAME,
                        }
                    )
                    if "homeAccessoryInfo" in peer_data:
                        peer_data["homeAccessoryInfo"].update(
                            {
                                "name": DEVICE_NAME,
                            }
                        )
                if "audio-session-coordination.system-info" in siri_info:
                    audio_system_info = siri_info[
                        "audio-session-coordination.system-info"
                    ]
                    if "mediaRemoteRouteIdentifier" in audio_system_info:
                        audio_system_info[
                            "mediaRemoteRouteIdentifier"
                        ] = MEDIA_REMOTE_ROUTE_IDENTIFIER


class AirPlayChannelAppleTVProxy(AbstractHAPChannel):
    """Base class for AirPlay channel connection proxies."""

    def __init__(
        self,
        name: str,
        loop: asyncio.AbstractEventLoop,
        verifier: PairVerifyProcedure,
        remote_address: str,
        remote_port: int,
        remote_salt: str,
        remote_output_info: str,
        remote_input_info: str,
        output_key: bytes,
        input_key: bytes,
    ) -> None:
        """Initialize a new AirPlayChannelAppleTVProxy instance."""
        self.name = name
        self.loop = loop
        self.verifier = verifier
        self.remote_address = remote_address
        self.remote_port = remote_port
        self.remote_salt = remote_salt
        self.remote_output_info = remote_output_info
        self.remote_input_info = remote_input_info
        self.remote_transport: Optional[asyncio.BaseTransport] = None
        self.remote_protocol: Optional[AbstractHAPChannel] = None
        self._connected_event: asyncio.Event = asyncio.Event()
        super().__init__(output_key, input_key)

    def connection_made(self, transport) -> None:
        """Client did connect to channel proxy."""
        super().connection_made(transport)
        task = self.loop.create_task(self._connect_to_remote())
        task.add_done_callback(lambda t: self.handle_received())

    def connection_lost(self, exc) -> None:
        """Handle that connection was lost to client."""
        super().connection_lost(exc)
        if self.remote_transport:
            self.remote_transport.close()
            self.remote_transport = None
            self.remote_protocol = None

    def close(self) -> None:
        """Close the channel."""
        if self.remote_transport:
            self.remote_transport.close()
            self.remote_transport = None
            self.remote_protocol = None
        super().close()

    def handle_received(self) -> None:
        """Handle received data that was put in buffer."""
        if not self._connected_event.is_set():
            return

        if self.buffer:
            _LOGGER.debug("%s received from Client: %s", self.name, self.buffer)
            self.remote_send(self.buffer)
            self.buffer = b""

    def remote_received(self, data: bytes) -> None:
        """Message was received from remote side of channel."""
        _LOGGER.debug("%s received from Apple TV: %s", self.name, data)
        self.send(data)

    def remote_send(self, data: bytes) -> None:
        """Send message to remote side of channel."""
        assert self.remote_protocol is not None
        self.remote_protocol.send(data)

    async def _connect_to_remote(self):
        self.remote_transport, self.remote_protocol = await setup_channel(
            lambda output_key, input_key: AirPlayChannelAppleTVForwarder(
                self, output_key, input_key
            ),
            self.verifier,
            self.remote_address,
            self.remote_port,
            self.remote_salt,
            self.remote_output_info,
            self.remote_input_info,
        )
        self._connected_event.set()


class AirPlayChannelAppleTVForwarder(AbstractHAPChannel):
    """Outgoing AirPlay channel connection."""

    def __init__(
        self,
        channel_proxy: AirPlayChannelAppleTVProxy,
        output_key: bytes,
        input_key: bytes,
    ) -> None:
        """Initialize a new AirPlayChannelxAppleTVForwarder instance."""
        self.channel_proxy = channel_proxy
        super().__init__(output_key, input_key)

    def connection_lost(self, exc) -> None:
        """Handle that connection was lost to device."""
        super().connection_lost(exc)
        self.channel_proxy.close()

    def handle_received(self) -> None:
        """Handle received data that was put in buffer."""
        self.buffer: bytes
        self.channel_proxy.remote_received(self.buffer)
        self.buffer = b""


class AirPlayEventChannelAppleTVProxy(AirPlayChannelAppleTVProxy):
    """AirPlay event channel connection proxy."""

    def __init__(
        self,
        loop: asyncio.AbstractEventLoop,
        verifier: PairVerifyProcedure,
        remote_address: str,
        remote_port: int,
        shared_key: bytes,
    ) -> None:
        """Initialize a new AirPlayEventChannelAppleTVProxy instance."""
        super().__init__(
            "Event channel",
            loop,
            verifier,
            remote_address,
            remote_port,
            EVENTS_SALT,
            EVENTS_READ_INFO,
            EVENTS_WRITE_INFO,
            hkdf_expand(
                EVENTS_SALT,
                EVENTS_WRITE_INFO,
                shared_key,
            ),
            hkdf_expand(
                EVENTS_SALT,
                EVENTS_READ_INFO,
                shared_key,
            ),
        )


class AirPlayDataStreamChannelAppleTVProxy(AirPlayChannelAppleTVProxy):
    """AirPlay data stream channel connection proxy."""

    def __init__(
        self,
        steam_id: int,
        loop: asyncio.AbstractEventLoop,
        verifier: PairVerifyProcedure,
        remote_address: str,
        remote_port: int,
        shared_key: bytes,
        seed: int,
    ) -> None:
        """Initialize a new AirPlayDataStreamChannelAppleTVProxy instance."""
        salt = DATASTREAM_SALT + str(seed & 0xFFFFFFFFFFFFFFFF)
        super().__init__(
            f"Data stream {steam_id} channel",
            loop,
            verifier,
            remote_address,
            remote_port,
            salt,
            DATASTREAM_OUTPUT_INFO,
            DATASTREAM_INPUT_INFO,
            hkdf_expand(
                salt,
                DATASTREAM_INPUT_INFO,
                shared_key,
            ),
            hkdf_expand(
                salt,
                DATASTREAM_OUTPUT_INFO,
                shared_key,
            ),
        )


class AirPlayAppleTVProxy(BasicHttpServer, BaseAirPlayServerAuth):
    """Implementation of a fake AirPlay device."""

    def __init__(
        self,
        loop: asyncio.AbstractEventLoop,
        address: str,
        port: int,
        properties: Optional[Mapping[str, str]],
        credentials: Optional[str],
    ) -> None:
        """Initialize a new instance of CompanionAppleTVProxy."""
        BaseAirPlayServerAuth.__init__(self, DEVICE_NAME)
        BasicHttpServer.__init__(self, self)
        self.loop = loop
        self.address = address
        self.port = port
        self.credentials: Optional[str] = credentials
        self.client_hap_session: Optional[HAPSession] = None
        self.client_encryption = False
        self.service = MutableService(
            None, Protocol.AirPlay, port, properties, credentials=credentials
        )
        self.connection: Optional[HttpConnection] = None
        self.verifier: Optional[PairVerifyProcedure] = None
        self._channel_servers: Dict[str, asyncio.AbstractServer] = {}
        self._connected_event: asyncio.Event = asyncio.Event()
        # routes that need special handling when proxied
        self.add_route("SETUP", ".*", self.handle_setup)
        self.add_route("TEARDOWN", ".*", self.handle_teardown)

    async def start(self) -> None:
        """Start the proxy instance."""
        self.connection = await http_connect(self.address, self.port)
        self.verifier = await verify_connection(
            extract_credentials(self.service), self.connection
        )
        self._connected_event.set()

    def enable_encryption(self, output_key: bytes, input_key: bytes) -> None:
        """Enable encryption with the specified keys."""
        self.client_hap_session = session = HAPSession()
        session.enable(output_key, input_key)

    def connection_made(self, transport):
        """Client did connect to proxy."""
        _LOGGER.debug("Client connected to AirPlay proxy")
        self.transport = transport

    def connection_lost(self, exc):
        """Handle that connection was lost to client."""
        _LOGGER.debug("Connection lost to client device: %s", exc)
        self.connection.close()
        for channel_server in self._channel_servers.values():
            channel_server.close()

    def process_received(self, data: bytes) -> bytes:
        """Process incoming data."""
        if self.client_hap_session:
            if not self.client_encryption:
                # start encrypting from an incoming request
                self.client_encryption = True
            data = self.client_hap_session.decrypt(data)
            _LOGGER.debug("Received (decrypted): %s", data)
        return data

    def process_sent(self, data: bytes) -> bytes:
        """Process outgoing data."""
        if self.client_encryption:
            assert self.client_hap_session is not None
            data = self.client_hap_session.encrypt(data)
            log_binary(_LOGGER, ">> Send", Encrypted=data)
        return data

    def handle_setup(self, request: HttpRequest):
        """Handle incoming SETUP request."""
        return self.loop.create_task(self._handle_setup(request))

    async def _handle_setup(self, request: HttpRequest):
        request_data = self._decode_plist_body(request.body)
        if "streams" in request_data:
            return await self._handle_setup_data_stream_channel(request, request_data)
        return await self._handle_setup_event_channel(request, request_data)

    async def _handle_setup_event_channel(
        self, request: HttpRequest, request_data: dict
    ):
        response = await self.send_to_atv(request)
        response_data = self._decode_plist_body(response.body)
        event_port = response_data["eventPort"]

        key = request.headers.get(
            "DACP-ID", request.headers.get("Active-Remote", request.path)
        )
        proxy_port = await self._create_channel_server(
            f"Event {key}",
            partial(self._create_event_channel, event_port),
        )
        _LOGGER.debug("Event port: remote=%d, local=%d", event_port, proxy_port)

        return response._replace(
            body=self._encode_plist_body(
                {
                    **response_data,
                    "eventPort": proxy_port,
                }
            )
        )

    async def _handle_setup_data_stream_channel(
        self, request: HttpRequest, request_data: dict
    ):
        request_data_streams = request_data["streams"]
        response = await self.send_to_atv(request)
        response_data = self._decode_plist_body(response.body)
        response_data_streams = response_data["streams"]

        response_data_streams_modified = []
        for request_stream, response_stream in zip(
            request_data_streams, response_data_streams
        ):
            stream_id = response_stream["streamID"]
            stream_port = response_stream["dataPort"]
            stream_seed = request_stream["seed"]

            proxy_port = await self._create_channel_server(
                f"Data stream {stream_id}",
                partial(
                    self._create_data_stream_channel,
                    stream_port,
                    stream_id,
                    stream_seed,
                ),
            )
            _LOGGER.debug(
                "Data stream %d port: remote=%d, local=%d",
                stream_id,
                stream_port,
                proxy_port,
            )

            response_data_streams_modified.append(
                {
                    **response_stream,
                    "dataPort": proxy_port,
                }
            )

        return response._replace(
            body=self._encode_plist_body(
                {
                    **response_data,
                    "streams": response_data_streams_modified,
                }
            )
        )

    def handle_teardown(self, request: HttpRequest):
        """Handle incoming TEARDOWN request."""
        return self.loop.create_task(self._handle_teardown(request))

    async def _handle_teardown(self, request: HttpRequest):
        request_data = self._decode_plist_body(request.body)
        if "streams" in request_data:
            return await self._handle_teardown_data_stream_channel(
                request, request_data
            )
        return await self._handle_teardown_event_channel(request, request_data)

    async def _handle_teardown_event_channel(
        self, request: HttpRequest, request_data: dict
    ):
        try:
            return await self.send_to_atv(request)
        except TimeoutError:
            pass
        finally:
            key = request.headers.get(
                "DACP-ID", request.headers.get("Active-Remote", request.path)
            )
            self._destroy_channel_server(f"Event {key}")

    async def _handle_teardown_data_stream_channel(
        self, request: HttpRequest, request_data: dict
    ):
        try:
            return await self.send_to_atv(request)
        except TimeoutError:
            pass
        finally:
            for request_stream in request_data["streams"]:
                stream_id = request_stream["streamID"]
                self._destroy_channel_server(f"Data stream {stream_id}")

    def handle_request(
        self, request: HttpRequest
    ) -> Optional[Union[HttpResponse, asyncio.Task]]:
        """Dispatch request to correct handler method or proxy to remote device."""
        self._log_request(request)
        response = super().handle_request(request)
        if response is not None:
            return response
        # proxy verbatim if there was no specific handler
        task = self.loop.create_task(self.send_to_atv(request))
        return task

    async def send_to_atv(self, request: HttpRequest) -> HttpResponse:
        """Forward request to remote device (ATV)."""
        await self._connected_event.wait()
        assert self.connection is not None
        response = await self.connection.send_and_receive(
            method=request.method,
            uri=request.path,
            protocol=f"{request.protocol}/{request.version}",
            headers=request.headers,
            body=request.body,
        )
        self._log_response(response)
        return response

    async def _create_channel_server(
        self, identifier: str, channel_factory: Callable[[], AirPlayChannelAppleTVProxy]
    ) -> int:
        server = await self.loop.create_server(channel_factory, "0.0.0.0")
        self._channel_servers[identifier] = server
        proxy_port = server.sockets[0].getsockname()[1]
        return proxy_port

    def _destroy_channel_server(self, identifier: str):
        server = self._channel_servers.pop(identifier, None)
        if server:
            server.close()

    def _create_event_channel(self, port: int) -> AirPlayEventChannelAppleTVProxy:
        assert self.connection is not None
        assert self.verifier is not None
        assert self.shared_key is not None
        return AirPlayEventChannelAppleTVProxy(
            self.loop,
            self.verifier,
            self.connection.remote_ip,
            port,
            self.shared_key,
        )

    def _create_data_stream_channel(
        self, port: int, stream_id: int, seed: int
    ) -> AirPlayDataStreamChannelAppleTVProxy:
        assert self.connection is not None
        assert self.verifier is not None
        assert self.shared_key is not None
        return AirPlayDataStreamChannelAppleTVProxy(
            stream_id,
            self.loop,
            self.verifier,
            self.connection.remote_ip,
            port,
            self.shared_key,
            seed,
        )

    def _log_request(self, request: HttpRequest) -> None:
        _LOGGER.debug("Request: %s", request)
        if request.headers.get(
            "content-type"
        ) == "application/x-apple-binary-plist" and (
            payload := self._decode_plist_body(request.body)
        ):
            _LOGGER.debug("%s request plist content: %s:", request.protocol, payload)

    def _log_response(self, response: HttpResponse) -> None:
        _LOGGER.debug("Response: %s", response)
        if response.headers.get(
            "content-type"
        ) == "application/x-apple-binary-plist" and (
            payload := self._decode_plist_body(response.body)
        ):
            _LOGGER.debug("%s response plist content: %s:", response.protocol, payload)

    def _decode_plist_body(self, body: Union[str, bytes]) -> dict:
        try:
            return plistlib.loads(
                body if isinstance(body, bytes) else body.encode("utf-8")
            )
        except plistlib.InvalidFileException:
            return {}

    def _encode_plist_body(self, data: dict):
        return plistlib.dumps(data, fmt=plistlib.PlistFormat.FMT_BINARY)


class RemoteConnection(asyncio.Protocol):
    """Connection to host of interest."""

    def __init__(self, loop):
        """Initialize a new RemoteConnection."""
        self.loop = loop
        self.transport = None
        self.callback = None

    def connection_made(self, transport):
        """Connect to host was established."""
        extra_info = transport.get_extra_info("socket")

        _LOGGER.debug("Connected to remote host %s", extra_info.getpeername())
        self.transport = transport

    def connection_lost(self, exc):
        """Lose connection to host."""
        _LOGGER.debug("Disconnected from remote host")
        self.transport = None

    def data_received(self, data):
        """Receive data from host."""
        log_binary(_LOGGER, "Data from remote", Data=data)
        self.callback.transport.write(data)


class RelayConnection(asyncio.Protocol):
    """Connection to initiating device, e.g. a phone."""

    def __init__(self, loop, connection):
        """Initialize a new RelayConnection."""
        self.loop = loop
        self.transport = None
        self.connection = connection

    def connection_made(self, transport):
        """Connect to host was established."""
        extra_info = transport.get_extra_info("socket")

        _LOGGER.debug("Client connected %s", extra_info.getpeername())
        self.transport = transport
        self.connection.callback = self

    def connection_lost(self, exc):
        """Lose connection to host."""
        _LOGGER.debug("Client disconnected")
        self.transport = None

    def data_received(self, data):
        """Receive data from host."""
        log_binary(_LOGGER, "Data from client", Data=data)
        self.connection.transport.write(data)


async def publish_mrp_service(zconf: Zeroconf, address: str, port: int, name: str):
    """Publish zeroconf service for ATV MRP proxy instance."""
    properties = {
        "ModelName": "Apple TV",
        "AllowPairing": "YES",
        "macAddress": "40:cb:c0:12:34:56",
        "BluetoothAddress": "False",
        "Name": name,
        "UniqueIdentifier": MRP_SERVER_IDENTIFIER,
        "SystemBuildVersion": "17K499",
        "LocalAirPlayReceiverPairingIdentity": AIRPLAY_IDENTIFIER,
    }

    return await mdns.publish(
        asyncio.get_event_loop(),
        mdns.Service(
            "_mediaremotetv._tcp.local", name, IPv4Address(address), port, properties
        ),
        zconf,
    )


async def publish_companion_service(
    zconf: Zeroconf, address: str, port: int, target_properties: Dict[str, str]
):
    """Publish zeroconf service for ATV Companion proxy instance."""
    properties = {
        **target_properties,
        "rpHA": "9948cfb6da55",
        "rpHN": "cef88e5db6fa",
        "rpAD": "3b2210518c58",
        "rpHI": "91756a18d8e5",
        "rpBA": BLUETOOTH_ADDRESS,
        "rpMRtID": MEDIA_REMOTE_ROUTE_IDENTIFIER,
    }

    return await mdns.publish(
        asyncio.get_event_loop(),
        mdns.Service(
            "_companion-link._tcp.local",
            DEVICE_NAME,
            IPv4Address(address),
            port,
            properties,
        ),
        zconf,
    )


async def publish_airplay_service(
    zconf: Zeroconf, address: str, port: int, target_properties: Dict[str, str]
):
    """Publish zeroconf service for ATV AirPlay proxy instance."""
    properties = {
        **target_properties,
    }

    return await mdns.publish(
        asyncio.get_event_loop(),
        mdns.Service(
            "_airplay._tcp.local",
            DEVICE_NAME,
            IPv4Address(address),
            port,
            properties,
        ),
        zconf,
    )


async def _start_mrp_proxy(loop, args, zconf: Zeroconf):
    def proxy_factory():
        try:
            proxy = MrpAppleTVProxy(
                loop, args.remote_ip, args.remote_port, args.credentials
            )
            asyncio.ensure_future(
                proxy.start(),
                loop=loop,
            )
        except Exception:
            _LOGGER.exception("failed to start proxy")
            raise
        return proxy

    if args.local_ip is None:
        args.local_ip = str(net.get_local_address_reaching(IPv4Address(args.remote_ip)))

    _LOGGER.debug("Binding to local address %s", args.local_ip)

    if not (args.remote_port or args.name):
        resp = await mdns.unicast(loop, args.remote_ip, ["_mediaremotetv._tcp.local"])

        if not args.remote_port:
            args.remote_port = resp.services[0].port
        if not args.name:
            args.name = resp.services[0].name + " Proxy"

    if not args.name:
        args.name = DEVICE_NAME

    # Setup server used to publish a fake MRP server
    server = await loop.create_server(proxy_factory, "0.0.0.0")
    port = server.sockets[0].getsockname()[1]
    _LOGGER.info("Started MRP server at port %d", port)

    unpublisher = await publish_mrp_service(zconf, args.local_ip, port, args.name)

    print("Press ENTER to quit")
    await loop.run_in_executor(None, sys.stdin.readline)

    return unpublisher


async def _start_companion_proxy(loop, args, zconf):
    def proxy_factory():
        try:
            proxy = CompanionAppleTVProxy(
                loop, args.remote_ip, args.remote_port, args.credentials
            )
            asyncio.ensure_future(
                proxy.start(),
                loop=loop,
            )
        except Exception:
            _LOGGER.exception("failed to start proxy")
            raise
        return proxy

    if args.local_ip is None:
        args.local_ip = str(net.get_local_address_reaching(IPv4Address(args.remote_ip)))

    _LOGGER.debug("Binding to local address %s", args.local_ip)

    service_type = "_companion-link._tcp.local"
    resp = await mdns.unicast(loop, args.remote_ip, [service_type])
    service = next((s for s in resp.services if s.type == service_type), None)

    if not args.remote_port:
        args.remote_port = service.port

    server = await loop.create_server(proxy_factory, "0.0.0.0")
    port = server.sockets[0].getsockname()[1]
    _LOGGER.info("Started Companion server at port %d", port)

    properties = {PROPERTY_CASE_MAP.get(k, k): v for k, v in service.properties.items()}
    unpublisher = await publish_companion_service(
        zconf, args.local_ip, port, properties
    )

    print("Press ENTER to quit")
    await loop.run_in_executor(None, sys.stdin.readline)

    return unpublisher


async def _start_airplay_proxy(loop, args, zconf):
    def proxy_factory():
        try:
            proxy = AirPlayAppleTVProxy(
                loop,
                args.remote_ip,
                args.remote_port,
                service.properties,
                args.credentials,
            )
            asyncio.ensure_future(
                proxy.start(),
                loop=loop,
            )
        except Exception:
            _LOGGER.exception("failed to start proxy")
            raise
        return proxy

    if args.local_ip is None:
        args.local_ip = str(net.get_local_address_reaching(IPv4Address(args.remote_ip)))

    _LOGGER.debug("Binding to local address %s", args.local_ip)

    service_type = "_airplay._tcp.local"
    resp = await mdns.unicast(loop, args.remote_ip, [service_type])
    service = next((s for s in resp.services if s.type == service_type), None)

    if not args.remote_port:
        args.remote_port = service.port

    server = await loop.create_server(proxy_factory, "0.0.0.0")
    port = server.sockets[0].getsockname()[1]
    _LOGGER.info("Started AirPlay server at port %d", port)

    unpublisher = await publish_airplay_service(
        zconf, args.local_ip, port, dict(service.properties)
    )

    print("Press ENTER to quit")
    await loop.run_in_executor(None, sys.stdin.readline)

    return unpublisher


async def _start_relay(loop, args, zconf):
    _, protocol = await loop.create_connection(
        lambda: RemoteConnection(loop), args.remote_ip, args.remote_port
    )

    coro = loop.create_server(lambda: RelayConnection(loop, protocol), "0.0.0.0")
    server = await loop.create_task(coro)
    port = server.sockets[0].getsockname()[1]

    props = dict({(prop.split("=")[0], prop.split("=")[1]) for prop in args.properties})

    unpublisher = await mdns.publish(
        asyncio.get_event_loop(),
        mdns.Service(
            args.service_type, args.name, IPv4Address(args.local_ip), port, props
        ),
        zconf,
    )

    print("Press ENTER to quit")
    await loop.run_in_executor(None, sys.stdin.readline)

    server.close()
    return unpublisher


async def appstart(loop):
    """Start the asyncio event loop and runs the application."""
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(title="sub-commands", dest="command")

    mrp = subparsers.add_parser("mrp", help="MRP proxy")
    mrp.add_argument("credentials", help="MRP credentials")
    mrp.add_argument("remote_ip", help="Apple TV IP address")
    mrp.add_argument("--name", default=None, help="proxy device name")
    mrp.add_argument("--local-ip", default=None, help="local IP address")
    mrp.add_argument("--remote_port", default=None, help="MRP port")

    companion = subparsers.add_parser("companion", help="Companion proxy")
    companion.add_argument("credentials", help="Companion credentials")
    companion.add_argument("remote_ip", help="Apple TV IP address")
    companion.add_argument("--local_ip", help="local IP address")
    companion.add_argument("--remote_port", help="Companion port")

    airplay = subparsers.add_parser("airplay", help="AirPlay proxy")
    airplay.add_argument("remote_ip", help="Apple TV IP address")
    airplay.add_argument("--credentials", help="AirPlay credentials")
    airplay.add_argument("--local_ip", help="local IP address")
    airplay.add_argument("--remote_port", help="AirPlay port")

    relay = subparsers.add_parser("relay", help="Relay traffic to host")
    relay.add_argument("local_ip", help="local IP address")
    relay.add_argument("remote_ip", help="Remote host")
    relay.add_argument("remote_port", help="Remote port")
    relay.add_argument("name", help="Service name")
    relay.add_argument("service_type", help="Service type")
    relay.add_argument("-p", "--properties", nargs="+", help="Service properties")

    args = parser.parse_args()
    if not args.command:
        parser.error("No command specified")
        return 1

    # To get logging from pyatv
    logging.basicConfig(
        level=logging.DEBUG,
        stream=sys.stdout,
        datefmt="%Y-%m-%d %H:%M:%S",
        format="%(asctime)s %(levelname)s [%(name)s]: %(message)s",
    )

    log_current_version()

    zconf = Zeroconf()
    if args.command == "mrp":
        unpublisher = await _start_mrp_proxy(loop, args, zconf)
    elif args.command == "companion":
        unpublisher = await _start_companion_proxy(loop, args, zconf)
    elif args.command == "airplay":
        unpublisher = await _start_airplay_proxy(loop, args, zconf)
    elif args.command == "relay":
        unpublisher = await _start_relay(loop, args, zconf)
    await unpublisher()

    return 0


def main():
    """Application start here."""
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(appstart(loop))


if __name__ == "__main__":
    sys.exit(main())
