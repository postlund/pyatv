#!/usr/bin/env python3
"""Simple proxy server to intercept traffic."""

import argparse
import asyncio
from ipaddress import IPv4Address
import logging
import sys
from typing import Any, Dict, Optional, cast

from google.protobuf.message import Message as ProtobufMessage
from zeroconf import Zeroconf

from pyatv.auth.hap_pairing import parse_credentials
from pyatv.auth.hap_srp import SRPAuthHandler
from pyatv.const import Protocol
from pyatv.core import MutableService, mdns
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
