#!/usr/bin/env python3
"""Set up a fake device."""
import os
import sys
import socket
import asyncio
import logging
import argparse

from aiozeroconf import Zeroconf, ServiceInfo

from pyatv.const import Protocol

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)) + "/..")  # noqa

from tests.fake_device import FakeAppleTV  # noqa

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
        except Exception:
            logging.exception("Exception in output loop")


async def publish_service(zconf, service, name, address, port, props):
    """Publish a Zeroconf service."""
    service = ServiceInfo(
        service,
        name + "." + service,
        address=socket.inet_aton(address),
        port=port,
        properties=props,
    )
    await zconf.register_service(service)
    _LOGGER.debug("Published zeroconf service: %s", service)

    return service


async def publish_mrp_zeroconf(zconf, address, port):
    """Publish MRP Zeroconf service."""
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
    return await publish_service(
        zconf, "_mediaremotetv._tcp.local.", DEVICE_NAME, address, port, props
    )


async def publish_dmap_zeroconf(zconf, address, port):
    """Publish DMAP Zeroconf service."""
    props = {
        b"DFID": b"2",
        b"PrVs": b"65538",
        b"hG": HSGID.encode(),
        b"Name": DEVICE_NAME.encode(),
        b"txtvers": b"1",
        b"atSV": b"65541",
        b"MiTPV": b"196611",
        b"EiTS": b"1",
        b"fs": b"2",
        b"MniT": b"167845888",
    }
    return await publish_service(
        zconf, "_appletv-v2._tcp.local.", "fakedev", address, port, props
    )


async def publish_airplay_zeroconf(zconf, address, port):
    """Publish AirPlay Zeroconf service."""
    props = {
        b"deviceid": b"00:01:02:03:04:05",
        b"model": b"AppleTV3,1",
        b"pi": b"4EE5AF58-7E5D-465A-935E-82E4DB74385D",
        b"flags": b"0x44",
        b"vv": b"2",
        b"features": b"0x5A7FFFF7,0xE",
        b"pk": b"3853c0e2ce3844727ca0cb1b86a3e3875e66924d2648d8f8caf71f8118793d98",  # noqa
        b"srcvers": b"220.68",
    }
    return await publish_service(
        zconf, "_airplay._tcp.local.", DEVICE_NAME, address, port, props
    )


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
    protocols.add_argument(
        "--mrp", default=False, action="store_true", help="enable MRP protocol"
    )
    protocols.add_argument(
        "--dmap", default=False, action="store_true", help="enable DMAP protocol"
    )
    protocols.add_argument(
        "--airplay", default=False, action="store_true", help="enable AirPlay protocol"
    )
    args = parser.parse_args()

    if not (args.mrp or args.dmap or args.airplay):
        parser.error("no protocol enabled (see --help)")

    level = logging.DEBUG if args.debug else logging.WARNING
    logging.basicConfig(
        level=level,
        stream=sys.stdout,
        datefmt="%Y-%m-%d %H:%M:%S",
        format="%(asctime)s %(levelname)s: %(message)s",
    )

    tasks = []
    services = []
    zconf = Zeroconf(loop)
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
        _, usecase = fake_atv.add_service(Protocol.AirPlay)

    await fake_atv.start()

    if args.mrp:
        services.append(
            await publish_mrp_zeroconf(
                zconf, args.local_ip, fake_atv.get_port(Protocol.MRP)
            )
        )

    if args.dmap:
        services.append(
            await publish_dmap_zeroconf(
                zconf, args.local_ip, fake_atv.get_port(Protocol.DMAP)
            )
        )

    if args.airplay:
        services.append(
            await publish_airplay_zeroconf(
                zconf, args.local_ip, fake_atv.get_port(Protocol.AirPlay)
            )
        )

    print("Press ENTER to quit")
    await loop.run_in_executor(None, sys.stdin.readline)

    await fake_atv.stop()

    for task in tasks:
        task.cancel()

    for service in services:
        await zconf.unregister_service(service)

    print("Exiting")

    return 0


def main():
    """Application start here."""
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(appstart(loop))


if __name__ == "__main__":
    sys.exit(main())
