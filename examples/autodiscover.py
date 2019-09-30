"""Simple example that connects to a device with autodiscover."""

import sys
import asyncio
import pyatv

LOOP = asyncio.get_event_loop()


# Method that is dispatched by the asyncio event loop
async def print_what_is_playing(loop):
    """Find a device and print what is playing."""
    print('Discovering devices on network...')
    atvs = await pyatv.scan_for_apple_tvs(loop, timeout=5)

    if not atvs:
        print('no device found', file=sys.stderr)
        return

    print('Connecting to {0}'.format(atvs[0].address))
    atv = await pyatv.connect_to_apple_tv(atvs[0], loop)

    try:
        playing = await atv.metadata.playing()
        print('Currently playing:')
        print(playing)
    finally:
        # Do not forget to logout
        await atv.logout()


if __name__ == '__main__':
    # Setup event loop and connect
    LOOP.run_until_complete(print_what_is_playing(LOOP))
