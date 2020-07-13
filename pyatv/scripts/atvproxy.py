#!/usr/bin/env python3
"""Simple proxy server to intercept traffic."""

import sys
import asyncio
import logging
import argparse
from ipaddress import IPv4Address

from zeroconf import Zeroconf

from pyatv.conf import MrpService
from pyatv.mrp.srp import SRPAuthHandler
from pyatv.mrp.connection import MrpConnection
from pyatv.mrp.protocol import MrpProtocol
from pyatv.mrp import chacha20, protobuf, variant
from pyatv.mrp.server_auth import MrpServerAuth, SERVER_IDENTIFIER
from pyatv.support import log_binary, net, mdns

_LOGGER = logging.getLogger(__name__)

DEVICE_NAME = "Proxy"
AIRPLAY_IDENTIFIER = "4D797FD3-3538-427E-A47B-A32FC6CF3A6A"


class MrpAppleTVProxy(MrpServerAuth, asyncio.Protocol):
    """Implementation of a fake MRP Apple TV."""

    def __init__(self, loop):
        """Initialize a new instance of ProxyMrpAppleTV."""
        super().__init__(self, DEVICE_NAME)
        self.loop = loop
        self.buffer = b""
        self.transport = None
        self.chacha = None
        self.connection = None

    async def start(self, address, port, credentials):
        """Start the proxy instance."""
        self.connection = MrpConnection(address, port, self.loop)
        protocol = MrpProtocol(
            self.connection,
            SRPAuthHandler(),
            MrpService(None, port, credentials=credentials),
        )
        await protocol.start(skip_initial_messages=True)
        self.connection.listener = self
        self._process_buffer()

    def connection_made(self, transport):
        """Client did connect to proxy."""
        self.transport = transport

    def enable_encryption(self, input_key, output_key):
        """Enable encryption with specified keys."""
        self.chacha = chacha20.Chacha20Cipher(input_key, output_key)

    def send(self, message):
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


async def publish_mrp_service(
    loop: asyncio.AbstractEventLoop, zconf: Zeroconf, address: str, port: int, name: str
):
    """Publish zeroconf service for ATV proxy instance."""
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


async def _start_mrp_proxy(loop, args, zconf: Zeroconf):
    def proxy_factory():
        try:
            proxy = MrpAppleTVProxy(loop)
            asyncio.ensure_future(
                proxy.start(args.remote_ip, args.remote_port, args.credentials),
                loop=loop,
            )
        except Exception:
            _LOGGER.exception("failed to start proxy")
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

    unpublisher = await publish_mrp_service(loop, zconf, args.local_ip, port, args.name)

    print("Press ENTER to quit")
    await loop.run_in_executor(None, sys.stdin.readline)

    return unpublisher


async def _start_relay(loop, args, zconf):
    transport, protocol = await loop.create_connection(
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
        format="%(asctime)s %(levelname)s: %(message)s",
    )

    zconf = Zeroconf()
    if args.command == "mrp":
        unpublisher = await _start_mrp_proxy(loop, args, zconf)
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
