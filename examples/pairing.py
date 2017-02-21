"""Simple example showing of pairing."""

import pyatv
import asyncio
from zeroconf import Zeroconf


PIN_CODE = 1234
REMOTE_NAME = 'my remote control'


# Method that is dispatched by the asyncio event loop
@asyncio.coroutine
def pair_with_device(loop):
    my_zeroconf = Zeroconf()
    handler = pyatv.pair_with_apple_tv(loop, PIN_CODE, REMOTE_NAME)

    yield from handler.start(my_zeroconf)
    print('You can now pair with pyatv')

    # Wait for a minute to allow pairing
    yield from asyncio.sleep(60, loop=loop)

    yield from handler.stop()

    # Give some feedback about the process
    if handler.has_paired:
        print('Paired with device!')
    else:
        print('Did not pair with device!')

    my_zeroconf.close()


# Setup event loop and connect
loop = asyncio.get_event_loop()
loop.run_until_complete(pair_with_device(loop))
