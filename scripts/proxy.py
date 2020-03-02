#!/usr/bin/env python3
#
# This is a hack to sort-of intercept traffic between an Apple TV and the iOS
# app. It will establish a connection to the ATV-of-interest (using code from
# pyatv to do so), publish a fake device called "ATVProxy" that can be paired
# with the app and forward messages between the two devices. Two sets of
# encryption keys are used: one set between ATV and this proxy and a second set
# between this proxy and the app. So all messages are "re-encrypted".
#
# What you need is:
#
# * Credentials to device of interest (atvremote -a --id <device> pair)
# * IP-address and port to the Apple TV of interest
# * IP-address of an interface that is on the same network as the Apple TV
#
# Then you just call this script like:
#
#   python ./scripts/proxy.py `cat credentials` 10.0.0.20 10.0.10.30 49152
#
# Argument order: <credentials> <local ip> <atv ip> <atv port>
#
# It shoulf be possible to pair with your phone using pin "1111". When the
# proxy receives a connection, it will start by connecting to the Apple TV and
# then continue with setting up encryption and relaying messages. The same
# static key pair is hardcoded, so it is possible to reconnect again layer
# without having to re-pair.
#
# Please note that this script is perhaps not a 100% accurate MITM of all
# traffic. It takes shortcuts and doesn't imitate everything correctly, so some
# traffic might be missed. Also note that printed protobuf messages are based
# on the definitions in pyatv. If new fields have been added by Apple, they
# will not be seen in the logs.
#
# Some suggestions for improvements:
#
# * Use pyatv to discover device (based on device id) to not have to enter all
#   details on command line
# * Use argparse for arguments
# * Base proxy device name on real device (e.g. Bedroom -> Bedroom Proxy)
# * Re-work logging to make it more clear what is what
# * General clean-ups
#
# Help to improve the proxy is greatly appreciated! I will only make
# improvements in case I personally see any benefits of doing so.
"""Simple MRP proxy server to intercept traffic."""

import os
import sys
import socket
import asyncio
import logging

from aiozeroconf import Zeroconf, ServiceInfo

from pyatv.conf import MrpService
from pyatv.mrp.srp import SRPAuthHandler
from pyatv.mrp.connection import MrpConnection
from pyatv.mrp.protocol import MrpProtocol
from pyatv.mrp import chacha20, protobuf, variant
from pyatv.support import log_binary

# SRP server auth lives with the test code for now and we need to add that path
# so python finds it. This should be removed once fake devices are part of the
# real library code.
sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)) + "/..")  # noqa

from tests.mrp.mrp_server_auth import MrpServerAuth, SERVER_IDENTIFIER

_LOGGER = logging.getLogger(__name__)

DEVICE_NAME = "Proxy"
AIRPLAY_IDENTIFIER = "4D797FD3-3538-427E-A47B-A32FC6CF3A6A"


class ProxyMrpAppleTV(MrpServerAuth, asyncio.Protocol):
    """Implementation of a fake MRP Apple TV."""

    def __init__(self, loop):
        """Initialize a new instance of ProxyMrpAppleTV."""
        super().__init__(self, DEVICE_NAME)
        self.loop = loop
        self.auther = MrpServerAuth(self, DEVICE_NAME)
        self.buffer = b""
        self.transport = None
        self.chacha = None
        self.connection = None

    async def start(self, address, port, credentials):
        """Start the proxy instance."""
        self.connection = MrpConnection(address, port, self.loop)
        protocol = MrpProtocol(
            self.loop,
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


async def publish_zeroconf(zconf, ip_address, port):
    """Publish zeroconf service for ATV proxy instance."""
    props = {
        b"ModelName": "Apple TV",
        b"AllowPairing": b"YES",
        b"macAddress": b"40:cb:c0:12:34:56",
        b"BluetoothAddress": False,
        b"Name": DEVICE_NAME.encode(),
        b"UniqueIdentifier": SERVER_IDENTIFIER.encode(),
        b"SystemBuildVersion": b"17K499",
        b"LocalAirPlayReceiverPairingIdentity": AIRPLAY_IDENTIFIER.encode(),
    }

    service = ServiceInfo(
        "_mediaremotetv._tcp.local.",
        DEVICE_NAME + "._mediaremotetv._tcp.local.",
        address=socket.inet_aton(ip_address),
        port=port,
        weight=0,
        priority=0,
        properties=props,
    )
    await zconf.register_service(service)
    _LOGGER.debug("Published zeroconf service: %s", service)

    return service


async def main(loop):
    """Script starts here."""
    # To get logging from pyatv
    logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)

    if len(sys.argv) != 5:
        print(
            "Usage: {0} <credentials> <local ip> "
            "<atv ip> <atv port>".format(sys.argv[0])
        )
        sys.exit(1)

    credentials = sys.argv[1]
    local_ip_addr = sys.argv[2]
    atv_ip_addr = sys.argv[3]
    atv_port = int(sys.argv[4])
    zconf = Zeroconf(loop)

    def proxy_factory():
        try:
            proxy = ProxyMrpAppleTV(loop)
            asyncio.ensure_future(
                proxy.start(atv_ip_addr, atv_port, credentials), loop=loop
            )
        except Exception:
            _LOGGER.exception("failed to start proxy")
        return proxy

    # Setup server used to publish a fake MRP server
    server = await loop.create_server(proxy_factory, "0.0.0.0")
    port = server.sockets[0].getsockname()[1]
    _LOGGER.error("Started MRP server at port %d", port)

    service = await publish_zeroconf(zconf, local_ip_addr, port)

    print("Press ENTER to quit")
    await loop.run_in_executor(None, sys.stdin.readline)

    await zconf.unregister_service(service)


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main(asyncio.get_event_loop()))
