"""Simple example that connects to a device with autodiscover."""

import asyncio
from pyatv import helpers


# Method that is dispatched by the asyncio event loop
@asyncio.coroutine
def print_what_is_playing(atv):
    """Print what is playing for the discovered device."""
    playing = yield from atv.metadata.playing()
    print('Currently playing:')
    print(playing)


# logout is automatically performed by auto_connect
helpers.auto_connect(print_what_is_playing)
