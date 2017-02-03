"""Simple example that connects to a device with autodiscover."""

import sys
import pyatv
import asyncio


# Method that is dispatched by the asyncio event loop
@asyncio.coroutine
def print_what_is_playing(loop):
    print('Discovering devices on network...')
    atvs = yield from pyatv.scan_for_apple_tvs(loop, timeout=5)

    if len(atvs) == 0:
        sys.stderr.print('no device found\n')
        return

    print('Connecting to {}'.format(atvs[0].address))
    atv = pyatv.connect_to_apple_tv(atvs[0], loop)

    try:
        playing = yield from atv.metadata.playing()
        print('Currently playing:')
        print(playing)
    finally:
        # Do not forget to logout
        yield from atv.logout()


# Setup event loop and connect
loop = asyncio.get_event_loop()
loop.run_until_complete(print_what_is_playing(loop))
