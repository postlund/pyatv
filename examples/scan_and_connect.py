"""Simple example that scans for devices and connects to first one found."""

import asyncio
import sys

import pyatv

LOOP = asyncio.get_event_loop()


# Method that is dispatched by the asyncio event loop
async def print_what_is_playing(loop):
    """Find a device and print what is playing."""
    print("Discovering devices on network...")
    atvs = await pyatv.scan(loop, timeout=5)

    if not atvs:
        print("No device found", file=sys.stderr)
        return

    print(f"Connecting to {atvs[0].address}")
    atv = await pyatv.connect(atvs[0], loop)

    try:
        playing = await atv.metadata.playing()
        print("Currently playing:")
        print(playing)
    finally:
        # Do not forget to close
        atv.close()


if __name__ == "__main__":
    # Setup event loop and connect
    LOOP.run_until_complete(print_what_is_playing(LOOP))
