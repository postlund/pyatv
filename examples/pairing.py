"""Simple example showing of pairing."""

import sys
import asyncio

import pyatv
from pyatv import const


LOOP = asyncio.get_event_loop()


# Method that is dispatched by the asyncio event loop
async def pair_with_device(loop):
    """Make it possible to pair with device."""
    atvs = await pyatv.scan(loop, timeout=5, protocol=const.PROTOCOL_MRP)

    if not atvs:
        print('No device found', file=sys.stderr)
        return

    pairing = await pyatv.pair(atvs[0], const.PROTOCOL_MRP, loop)
    await pairing.begin()

    pin = int(input("Enter PIN: "))
    pairing.pin(pin)
    await pairing.finish()

    # Give some feedback about the process
    if pairing.has_paired:
        print('Paired with device!')
        print('Credentials:', pairing.credentials)
    else:
        print('Did not pair with device!')


if __name__ == '__main__':
    # Setup event loop and connect
    LOOP.run_until_complete(pair_with_device(LOOP))
