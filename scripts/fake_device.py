#!/usr/bin/env python3
"""Set up a fake device.

Currently only supports MRP.
"""
import sys
import os
import socket
import asyncio
import logging
import argparse

from aiozeroconf import Zeroconf, ServiceInfo

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)) + "/..")  # noqa

from tests.mrp.fake_mrp_atv import FakeAppleTV, FakeDeviceState

_LOGGER = logging.getLogger(__name__)

DEVICE_NAME = "FakeMRP"
AIRPLAY_IDENTIFIER = "4D797FD3-3538-427E-A47B-A32FC6CF3A6A"

SERVER_IDENTIFIER = "6D797FD3-3538-427E-A47B-A32FC6CF3A69"


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


async def appstart(loop):
    """Script starts here."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--local-ip", default="127.0.0.1", help="local IP address")
    parser.add_argument(
        "-d", "--debug", default=False, action="store_true", help="enable debug logs"
    )
    args = parser.parse_args()

    level = logging.DEBUG if args.debug else logging.WARNING
    logging.basicConfig(level=level, stream=sys.stdout)

    state = FakeDeviceState()
    zconf = Zeroconf(loop)
    server = await loop.create_server(lambda: FakeAppleTV(loop, state=state), "0.0.0.0")
    port = server.sockets[0].getsockname()[1]
    _LOGGER.info("Started fake MRP device at port %d", port)

    service = await publish_zeroconf(zconf, args.local_ip, port)

    print("Press ENTER to quit")
    await loop.run_in_executor(None, sys.stdin.readline)

    await zconf.unregister_service(service)

    return 0


def main():
    """Application start here."""
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(appstart(loop))


if __name__ == "__main__":
    sys.exit(main())
