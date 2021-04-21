"""Simple example showing of pairing."""

import asyncio
import sys

from pyatv import pair, scan
from pyatv.const import Protocol

LOOP = asyncio.get_event_loop()


# Method that is dispatched by the asyncio event loop
async def pair_with_device(loop):
    """Make it possible to pair with device."""
    atvs = await scan(loop, timeout=5, protocol=Protocol.MRP)

    if not atvs:
        print("No device found", file=sys.stderr)
        return

    pairing = await pair(atvs[0], Protocol.MRP, loop)
    await pairing.begin()

    pin = int(input("Enter PIN: "))
    pairing.pin(pin)
    await pairing.finish()

    # Give some feedback about the process
    if pairing.has_paired:
        print("Paired with device!")
        print("Credentials:", pairing.service.credentials)
    else:
        print("Did not pair with device!")

    await pairing.close()


if __name__ == "__main__":
    # Setup event loop and connect
    LOOP.run_until_complete(pair_with_device(LOOP))
