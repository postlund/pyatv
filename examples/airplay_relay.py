"""Control existing AirPlay playback using pyatv's public interfaces."""

import argparse
import asyncio

import pyatv
from pyatv.const import Protocol
from pyatv.settings import MrpTunnel
from pyatv.storage.memory_storage import MemoryStorage


async def main() -> None:
    """Discover a receiver, opt into its relay, and perform one requested action."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("name", help="Exact name of the AirPlay receiver")
    parser.add_argument(
        "action",
        nargs="?",
        default="status",
        choices=["status", "play", "pause", "next", "previous", "seek", "volume"],
    )
    parser.add_argument(
        "value", nargs="?", type=float, help="Seconds or volume (0–100)"
    )
    args = parser.parse_args()
    if args.action in ("seek", "volume") and args.value is None:
        parser.error("seek and volume require a value")

    loop = asyncio.get_running_loop()
    storage = MemoryStorage()
    devices = await pyatv.scan(loop, protocol=Protocol.AirPlay, storage=storage)
    config = next((device for device in devices if device.name == args.name), None)
    if config is None:
        print(f"Receiver not found: {args.name}")
        return
    settings = await storage.get_settings(config)
    settings.protocols.airplay.mrp_tunnel = MrpTunnel.Relay
    atv = await pyatv.connect(config, loop, storage=storage)
    try:
        print(await atv.metadata.playing())
        if args.action == "seek":
            await atv.remote_control.set_position(args.value)
        elif args.action == "volume":
            await atv.audio.set_volume(args.value)
        elif args.action != "status":
            await getattr(atv.remote_control, args.action)()
    finally:
        await asyncio.gather(*atv.close())


if __name__ == "__main__":
    asyncio.run(main())
