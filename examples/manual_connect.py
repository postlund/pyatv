"""Simple example that shows how to manually connect to an Apple TV."""

import pyatv
import asyncio

# Enter details used to connect
NAME = 'My Apple TV'
ADDRESS = '10.0.10.22'
HSGID = '00000000-1111-2222-3333-444444444444'
DETAILS = pyatv.AppleTVDevice(NAME, ADDRESS, HSGID)


# Method that is dispatched by the asyncio event loop
@asyncio.coroutine
def print_what_is_playing(loop, details):
    print('Connecting to {}'.format(details.address))
    atv = pyatv.connect_to_apple_tv(details, loop)

    try:
        playing = yield from atv.metadata.playing()
        print('Currently playing:')
        print(playing)
    except:
        # Do not forget to logout
        yield from atv.logout()


# Setup event loop and connect
loop = asyncio.get_event_loop()
loop.run_until_complete(print_what_is_playing(loop, DETAILS))
