"""Simple example that shows how to manually connect to an Apple TV."""

import sys
import asyncio
import pyatv
from pyatv import conf

# Enter details used to connect
NAME = 'My Apple TV'
ADDRESS = '10.0.10.22'
HSGID = '00000000-1111-2222-3333-444444444444'

LOOP = asyncio.get_event_loop()


# Method that is dispatched by the asyncio event loop
async def print_what_is_playing(loop):
    """Connect to device and print what is playing."""
    device_id = pyatv.get_device_id(ADDRESS, loop)
    if device_id is None:
        print('Unable to determine device id', file=sys.stderr)
        sys.exit(1)

    details = conf.AppleTV(ADDRESS, device_id, NAME)
    details.add_service(conf.DmapService(HSGID))

    print('Connecting to {}'.format(details.address))
    atv = await pyatv.connect_to_apple_tv(details, loop)

    try:
        print((await atv.metadata.playing()))
    finally:
        # Do not forget to logout
        await atv.logout()


if __name__ == '__main__':
    # Setup event loop and connect
    LOOP.run_until_complete(print_what_is_playing(LOOP))
