"""Simple example showing of pairing."""

import pyatv
import asyncio


PIN_CODE = 1234
REMOTE_NAME = 'my remote control'


# Method that is dispatched by the asyncio event loop
@asyncio.coroutine
def pair_with_device(loop):
    handler = pyatv.pair_with_apple_tv(loop, PIN_CODE, REMOTE_NAME)

    yield from handler.start()
    print('You can now pair with pyatv')

    # Wait for a minute to allow pairing
    yield from asyncio.sleep(60, loop=loop)

    yield from handler.stop()


# Setup event loop and connect
loop = asyncio.get_event_loop()
loop.run_until_complete(pair_with_device(loop))
