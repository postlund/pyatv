"""Simple example that shows how to manually connect to an Apple TV."""
import asyncio

from pyatv import conf, connect

# Enter config used to connect
NAME = 'My Apple TV'
ADDRESS = '10.0.10.22'
HSGID = '00000000-1111-2222-3333-444444444444'

LOOP = asyncio.get_event_loop()


# Method that is dispatched by the asyncio event loop
async def print_what_is_playing(loop):
    """Connect to device and print what is playing."""
    config = conf.AppleTV(ADDRESS, NAME)
    config.add_service(conf.DmapService('some_id', HSGID))

    print('Connecting to {0}'.format(config.address))
    atv = await connect(config, loop)

    try:
        print(await atv.metadata.playing())
    finally:
        # Do not forget to close
        await atv.close()


if __name__ == '__main__':
    # Setup event loop and connect
    LOOP.run_until_complete(print_what_is_playing(LOOP))
