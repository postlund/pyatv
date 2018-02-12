"""Simple example showing of pairing."""

import asyncio
from zeroconf import Zeroconf

import pyatv
from pyatv import conf


PIN_CODE = 1234
REMOTE_NAME = 'my remote control'

LOOP = asyncio.get_event_loop()


# Method that is dispatched by the asyncio event loop
@asyncio.coroutine
def pair_with_device(loop):
    """Make it possible to pair with device."""
    my_zeroconf = Zeroconf()
    details = conf.AppleTV('127.0.0.1', 'Apple TV')
    details.add_service(conf.DmapService('login_id'))
    atv = pyatv.connect_to_apple_tv(details, loop)

    yield from atv.pairing.start(
        zeroconf=my_zeroconf, name=REMOTE_NAME, pin=PIN_CODE)
    print('You can now pair with pyatv')

    # Wait for a minute to allow pairing
    yield from asyncio.sleep(60, loop=loop)

    yield from atv.pairing.stop()

    # Give some feedback about the process
    if atv.pairing.has_paired:
        pairing_guid = yield from atv.pairing.get('pairing_gui')
        print('Paired with device!')
        print('Pairing guid: ' + pairing_guid)
    else:
        print('Did not pair with device!')

    my_zeroconf.close()


if __name__ == '__main__':
    # Setup event loop and connect
    LOOP.run_until_complete(pair_with_device(LOOP))
