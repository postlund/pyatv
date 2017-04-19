"""Simple example that shows how to manually connect to an Apple TV."""

import asyncio
import pyatv

# Enter details used to connect
NAME = 'My Apple TV'
ADDRESS = '10.0.10.22'
HSGID = '00000000-1111-2222-3333-444444444444'
DETAILS = pyatv.AppleTVDevice(NAME, ADDRESS, HSGID)

LOOP = asyncio.get_event_loop()


# Method that is dispatched by the asyncio event loop
@asyncio.coroutine
def print_what_is_playing(loop, details):
    """Connect to device and print what is playing."""
    print('Connecting to {}'.format(details.address))
    atv = pyatv.connect_to_apple_tv(details, loop)

    try:
        print((yield from atv.metadata.playing()))
    finally:
        # Do not forget to logout
        yield from atv.logout()


if __name__ == '__main__':
    # Setup event loop and connect
    LOOP.run_until_complete(print_what_is_playing(LOOP, DETAILS))
