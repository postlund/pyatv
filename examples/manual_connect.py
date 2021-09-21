"""Simple example that shows how to manually connect to an Apple TV."""
import asyncio

from pyatv import conf, connect
from pyatv.const import Protocol

# Enter config used to connect
NAME = "My Apple TV"
ADDRESS = "10.0.10.22"
HSGID = "00000000-1111-2222-3333-444444444444"

LOOP = asyncio.get_event_loop()


# Method that is dispatched by the asyncio event loop
async def print_what_is_playing(loop):
    """Connect to device and print what is playing."""
    config = conf.AppleTV(ADDRESS, NAME)
    config.add_service(
        conf.ManualService("some_id", Protocol.DMAP, 3689, {}, credentials=HSGID)
    )

    print(f"Connecting to {config.address}")
    atv = await connect(config, loop)

    try:
        print(await atv.metadata.playing())
    finally:
        # Do not forget to close
        atv.close()


if __name__ == "__main__":
    # Setup event loop and connect
    LOOP.run_until_complete(print_what_is_playing(LOOP))
