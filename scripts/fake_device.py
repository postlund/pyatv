#!/usr/bin/env python3
"""Set up a fake device.

Currently only supports MRP.
"""
import os
import sys
import socket
import asyncio
import logging
import argparse

from aiozeroconf import Zeroconf, ServiceInfo

from pyatv.const import Protocol

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)) + "/..")  # noqa

from tests.fake_device import FakeAppleTV

_LOGGER = logging.getLogger(__name__)

DEVICE_NAME = "FakeMRP"
AIRPLAY_IDENTIFIER = "4D797FD3-3538-427E-A47B-A32FC6CF3A6A"

SERVER_IDENTIFIER = "6D797FD3-3538-427E-A47B-A32FC6CF3A69"


async def _alter_playing(usecase):
    while True:
        try:
            logging.debug("Starting new output lap")
            usecase.example_video()
            await asyncio.sleep(3)
            usecase.example_music()
            await asyncio.sleep(3)
            usecase.nothing_playing()
            await asyncio.sleep(3)
        except asyncio.CancelledError:
            break
        except Exception:
            logging.exception("Exception in output loop")


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
        "--demo", default=False, action="store_true", help="enable demo mode"
    )
    parser.add_argument(
        "-d", "--debug", default=False, action="store_true", help="enable debug logs"
    )

    protocols = parser.add_argument_group("protocols")
    parser.add_argument(
        "--mrp", default=False, action="store_true", help="enable MRP protocol"
    )
    args = parser.parse_args()

    if not args.mrp:
        parser.error("no protocol enabled (see --help)")

    level = logging.DEBUG if args.debug else logging.WARNING
    logging.basicConfig(
        level=level,
        stream=sys.stdout,
        datefmt="%Y-%m-%d %H:%M:%S",
        format="%(asctime)s %(levelname)s: %(message)s",
    )

    tasks = []
    zconf = Zeroconf(loop)
    fake_atv = FakeAppleTV(loop)
    if args.mrp:
        _, usecase = fake_atv.add_service(Protocol.MRP)
        if args.demo:
            tasks.append(asyncio.ensure_future(_alter_playing(usecase)))

    await fake_atv.start()

    service = await publish_zeroconf(
        zconf, args.local_ip, fake_atv.get_port(Protocol.MRP)
    )

    print("Press ENTER to quit")
    await loop.run_in_executor(None, sys.stdin.readline)

    for task in tasks:
        task.cancel()

    await zconf.unregister_service(service)

    print("Exiting")

    return 0


def main():
    """Application start here."""
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(appstart(loop))


if __name__ == "__main__":
    sys.exit(main())
