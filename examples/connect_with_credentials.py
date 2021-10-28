"""Find a specific device, restore credentials and connect.

Call script like this:

    python connect_with_credentials.py 0

This connect to the first device in DEVICES (index 0). If you add
another device, use 1 instead of 0 and so on. You can easily
look up based on name as well (not demonstrated here).
"""

import asyncio
import sys

import pyatv
from pyatv.const import Protocol

LOOP = asyncio.get_event_loop()

# This can be stored in a file for instance
DEVICES = [
    {
        "name": "Living Room",
        "identifiers": {"aabbccddeeff", "123456789"},
        "credentials": {
            Protocol.AirPlay: "abcdef",
            Protocol.Companion: "foobar",
            Protocol.RAOP: "123456",
        },
    },
    # Add more devices here
]


async def print_what_is_playing(device, loop):
    """Find a device and print what is playing."""
    print(f"Discovering {device['name']} on network...")
    confs = await pyatv.scan(loop, identifier=device["identifiers"])

    if not confs:
        print("Device could not be found", file=sys.stderr)
        return

    conf = confs[0]
    for protocol, credentials in device["credentials"].items():
        conf.set_credentials(protocol, credentials)

    print(f"Connecting to {conf.address}")
    atv = await pyatv.connect(conf, loop)

    try:
        playing = await atv.metadata.playing()
        print("Currently playing:")
        print(playing)
    finally:
        await asyncio.gather(*atv.close())


if __name__ == "__main__":
    LOOP.run_until_complete(print_what_is_playing(DEVICES[int(sys.argv[1])], LOOP))
