"""Simple example showing of pairing."""

import sys
import asyncio
from aiozeroconf import Zeroconf

import pyatv


PIN_CODE = 1234
REMOTE_NAME = 'my remote control'

LOOP = asyncio.get_event_loop()


# Method that is dispatched by the asyncio event loop
async def pair_with_device(loop):
    """Make it possible to pair with device."""
    my_zeroconf = Zeroconf(loop)

    atvs = await pyatv.scan_for_apple_tvs(loop, timeout=5)

    if not atvs:
        print('no device found', file=sys.stderr)
        return

    atv = await pyatv.connect_to_apple_tv(atvs[0], loop)

    atv.pairing.pin(PIN_CODE)
    await atv.pairing.start(zeroconf=my_zeroconf, name=REMOTE_NAME)
    print('You can now pair with pyatv')

    # Wait for a minute to allow pairing
    await asyncio.sleep(60, loop=loop)

    await atv.pairing.stop()

    # Give some feedback about the process
    if atv.pairing.has_paired:
        print('Paired with device!')
        print('Credentials:', atv.pairing.credentials)
    else:
        print('Did not pair with device!')

    my_zeroconf.close()


if __name__ == '__main__':
    # Setup event loop and connect
    LOOP.run_until_complete(pair_with_device(LOOP))
