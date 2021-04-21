#!/usr/bin/env python3
"""Set up a fake device."""
import argparse
import asyncio
from ipaddress import IPv4Address
import logging
import os
import sys

from zeroconf import Zeroconf

from pyatv.const import Protocol
from pyatv.support import mdns

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)) + "/..")  # noqa

from tests.fake_device import (  # pylint: disable=wrong-import-position  # noqa
    FakeAppleTV,
)

_LOGGER = logging.getLogger(__name__)

DEVICE_NAME = "FakeATV"
AIRPLAY_IDENTIFIER = "4D797FD3-3538-427E-A47B-A32FC6CF3A6A"

SERVER_IDENTIFIER = "6D797FD3-3538-427E-A47B-A32FC6CF3A69"

HSGID = "12345678-6789-1111-2222-012345678911"
PAIRING_GUID = "0x0000000000000001"
SESSION_ID = 55555


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
        except Exception:  # pylint: disable=broad-except
            logging.exception("Exception in output loop")


async def publish_mrp_zeroconf(loop, zconf, address, port):
    """Publish MRP Zeroconf service."""
    props = {
        "ModelName": "Apple TV",
        "AllowPairing": "YES",
        "macAddress": "40:cb:c0:12:34:56",
        "BluetoothAddress": False,
        "Name": DEVICE_NAME,
        "UniqueIdentifier": SERVER_IDENTIFIER,
        "SystemBuildVersion": "17K499",
        "LocalAirPlayReceiverPairingIdentity": AIRPLAY_IDENTIFIER,
    }
    return await mdns.publish(
        loop,
        mdns.Service(
            "_mediaremotetv._tcp.local", DEVICE_NAME, IPv4Address(address), port, props
        ),
        zconf,
    )


async def publish_dmap_zeroconf(loop, zconf, address, port):
    """Publish DMAP Zeroconf service."""
    props = {
        "DFID": "2",
        "PrVs": "65538",
        "hG": HSGID,
        "Name": DEVICE_NAME,
        "txtvers": "1",
        "atSV": "65541",
        "MiTPV": "196611",
        "EiTS": "1",
        "fs": "2",
        "MniT": "167845888",
    }
    return await mdns.publish(
        loop,
        mdns.Service(
            "_appletv-v2._tcp.local", DEVICE_NAME, IPv4Address(address), port, props
        ),
        zconf,
    )


async def publish_airplay_zeroconf(loop, zconf, address, port):
    """Publish AirPlay Zeroconf service."""
    props = {
        "deviceid": "00:01:02:03:04:05",
        "model": "AppleTV3,1",
        "pi": "4EE5AF58-7E5D-465A-935E-82E4DB74385D",
        "flags": "0x44",
        "vv": "2",
        "features": "0x5A7FFFF7,0xE",
        "pk": "3853c0e2ce3844727ca0cb1b86a3e3875e66924d2648d8f8caf71f8118793d98",  # pylint: disable=line-too-long # noqa
        "srcvers": "220.68",
    }
    return await mdns.publish(
        loop,
        mdns.Service(
            "_airplay._tcp.local", DEVICE_NAME, IPv4Address(address), port, props
        ),
        zconf,
    )


async def publish_companion_zeroconf(loop, zconf, address, port):
    """Publish Companion Zeroconf service."""
    props = {
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
        loop,
        mdns.Service(
            "_companion-link._tcp.local", DEVICE_NAME, IPv4Address(address), port, props
        ),
        zconf,
    )


async def appstart(loop):  # pylint: disable=too-many-branches
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
    protocols.add_argument(
        "--mrp", default=False, action="store_true", help="enable MRP protocol"
    )
    protocols.add_argument(
        "--dmap", default=False, action="store_true", help="enable DMAP protocol"
    )
    protocols.add_argument(
        "--airplay", default=False, action="store_true", help="enable AirPlay protocol"
    )
    protocols.add_argument(
        "--companion",
        default=False,
        action="store_true",
        help="enable Companion protocol",
    )
    args = parser.parse_args()

    if not (args.mrp or args.dmap or args.airplay or args.companion):
        parser.error("no protocol enabled (see --help)")

    level = logging.DEBUG if args.debug else logging.WARNING
    logging.basicConfig(
        level=level,
        stream=sys.stdout,
        datefmt="%Y-%m-%d %H:%M:%S",
        format="%(asctime)s %(levelname)s: %(message)s",
    )

    tasks = []
    unpublishers = []
    zconf = Zeroconf()
    fake_atv = FakeAppleTV(loop, test_mode=False)
    if args.mrp:
        _, usecase = fake_atv.add_service(Protocol.MRP)
        if args.demo:
            tasks.append(asyncio.ensure_future(_alter_playing(usecase)))

    if args.dmap:
        _, usecase = fake_atv.add_service(
            Protocol.DMAP, hsgid=HSGID, pairing_guid=PAIRING_GUID, session_id=SESSION_ID
        )
        if args.demo:
            tasks.append(asyncio.ensure_future(_alter_playing(usecase)))

    if args.airplay:
        fake_atv.add_service(Protocol.AirPlay)

    if args.companion:
        fake_atv.add_service(Protocol.Companion)

    await fake_atv.start()

    if args.mrp:
        unpublishers.append(
            await publish_mrp_zeroconf(
                loop, zconf, args.local_ip, fake_atv.get_port(Protocol.MRP)
            )
        )

    if args.dmap:
        unpublishers.append(
            await publish_dmap_zeroconf(
                loop, zconf, args.local_ip, fake_atv.get_port(Protocol.DMAP)
            )
        )

    if args.airplay:
        unpublishers.append(
            await publish_airplay_zeroconf(
                loop, zconf, args.local_ip, fake_atv.get_port(Protocol.AirPlay)
            )
        )

    if args.companion:
        unpublishers.append(
            await publish_companion_zeroconf(
                loop, zconf, args.local_ip, fake_atv.get_port(Protocol.Companion)
            )
        )

    print("Press ENTER to quit")
    await loop.run_in_executor(None, sys.stdin.readline)

    await fake_atv.stop()

    for task in tasks:
        task.cancel()

    for unpublisher in unpublishers:
        await unpublisher()

    print("Exiting")

    return 0


def main():
    """Application start here."""
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(appstart(loop))


if __name__ == "__main__":
    sys.exit(main())
