#!/usr/bin/env python3
"""Simple proxy server to intercept traffic."""

import argparse
import asyncio
from ipaddress import IPv4Address
import logging
import sys
from typing import Optional

from google.protobuf.message import Message as ProtobufMessage
from zeroconf import Zeroconf

from pyatv.auth.hap_srp import SRPAuthHandler
from pyatv.const import Protocol
from pyatv.core import MutableService, mdns
from pyatv.protocols.companion import opack
from pyatv.protocols.companion.connection import CompanionConnection
from pyatv.protocols.companion.protocol import CompanionProtocol, FrameType
from pyatv.protocols.companion.server_auth import CompanionServerAuth
from pyatv.protocols.mrp import protobuf
from pyatv.protocols.mrp.connection import MrpConnection
from pyatv.protocols.mrp.protocol import MrpProtocol
from pyatv.protocols.mrp.server_auth import SERVER_IDENTIFIER, MrpServerAuth
from pyatv.support import chacha20, log_binary, net, variant

_LOGGER = logging.getLogger(__name__)

DEVICE_NAME = "Proxy"
AIRPLAY_IDENTIFIER = "4D797FD3-3538-427E-A47B-A32FC6CF3A6A"

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


class CompanionAppleTVProxy(CompanionServerAuth, asyncio.Protocol):
    """Implementation of a fake Companion device."""

    def __init__(
        self, loop: asyncio.AbstractEventLoop, address: str, port: int, credentials: str
    ) -> None:
        """Initialize a new instance of CompanionAppleTVProxy."""
        super().__init__(DEVICE_NAME)
        self.loop = loop
        self.buffer: bytes = b""
        self.transport = None
        self.chacha: Optional[chacha20.Chacha20Cipher] = None
        self.connection: Optional[CompanionConnection] = CompanionConnection(
            self.loop, address, port
        )
        self.protocol: CompanionProtocol = CompanionProtocol(
            self.connection,
            SRPAuthHandler(),
            MutableService(None, Protocol.Companion, port, {}, credentials=credentials),
        )
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
                resp = await self.send_to_atv(frame_type, data)
                self.send_to_client(frame_type, resp)
            except Exception:
                _LOGGER.exception("data exchange failed")

        self._receive_event.clear()

    def connection_made(self, transport):
        """Client did connect to proxy."""
        _LOGGER.debug("Client connected to Companion proxy")
        self.transport = transport

    def connection_lost(self, exc):
        """Handle that connection was lost to client."""
        _LOGGER.debug("Connection lost to client device: %s", exc)
        if self._receive_task is not None:
            self._receive_task.cancel()

    def data_received(self, data):
        """Message received from client (iOS)."""
        log_binary(_LOGGER, "Data from client", Data=data)
        self.buffer += data
        if self.connection.connected:
            self._receive_event.set()

    async def send_to_atv(self, frame_type: FrameType, data: bytes):
        """Send data to remote device (ATV)."""
        log_binary(_LOGGER, f">>(ENCRYPTED) FrameType={frame_type}", Message=data)

        if self.chacha:
            header = bytes([frame_type.value]) + len(data).to_bytes(3, byteorder="big")
            data = self.chacha.decrypt(data, aad=header)
            log_binary(_LOGGER, "<<(DECRYPTED)", Message=data)

        unpacked = opack.unpack(data)[0]
        return await self.protocol.exchange_opack(frame_type, unpacked)

    def send_to_client(self, frame_type: FrameType, data: object) -> None:
        """Send data to client device (iOS)."""
        if not self.transport:
            _LOGGER.error("Tried to send to client, but not connected")
            return

        payload = opack.pack(data)

        payload_length = len(payload) + (16 if self.chacha else 0)
        header = bytes([frame_type.value]) + payload_length.to_bytes(3, byteorder="big")

        if self.chacha:
            payload = self.chacha.encrypt(payload, aad=header)
            log_binary(_LOGGER, ">> Send", Header=header, Encrypted=payload)

        self.transport.write(header + payload)


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
        "UniqueIdentifier": SERVER_IDENTIFIER,
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


async def publish_companion_service(zconf: Zeroconf, address: str, port: int):
    """Publish zeroconf service for ATV Companion proxy instance."""
    properties = {
        "rpMac": "1",
        "rpHA": "9948cfb6da55",
        "rpHN": "88f979f04023",
        "rpVr": "230.1",
        "rpMd": "AppleTV6,2",
        "rpFl": "0x36782",
        "rpAD": "657c1b9d3484",
        "rpHI": "91756a18d8e5",
        "rpBA": "9D:19:F9:74:65:EA",
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
        else:
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
        else:
            return proxy

    if args.local_ip is None:
        args.local_ip = str(net.get_local_address_reaching(IPv4Address(args.remote_ip)))

    _LOGGER.debug("Binding to local address %s", args.local_ip)

    if not args.remote_port:
        resp = await mdns.unicast(loop, args.remote_ip, ["_companion-link._tcp.local"])

        if not args.remote_port:
            args.remote_port = resp.services[0].port

    server = await loop.create_server(proxy_factory, "0.0.0.0")
    port = server.sockets[0].getsockname()[1]
    _LOGGER.info("Started Companion server at port %d", port)

    unpublisher = await publish_companion_service(zconf, args.local_ip, port)

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
