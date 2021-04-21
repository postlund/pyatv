"""Simple example that connects to a device with autodiscover."""

import asyncio

from pyatv import helpers


# Method that is dispatched by the asyncio event loop
async def print_what_is_playing(atv):
    """Print what is playing for the discovered device."""
    playing = await atv.metadata.playing()
    print("Currently playing:")
    print(playing)


asyncio.get_event_loop().run_until_complete(helpers.auto_connect(print_what_is_playing))
