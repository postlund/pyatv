"""Various helper methods."""

import asyncio
import pyatv


def auto_connect(handler, timeout=5, not_found=None, event_loop=None):
    """Convenient method for connecting to a device.

    This is a convenience method that create an event loop, auto discovers
    devices, picks the first device found, connects to it and passes it to a
    user provided handler. An optional error handler can be provided that is
    called when no device was found. Very inflexible in many cases, but can be
    handys sometimes when trying things.

    Note 1: both handler and not_found must be coroutines
    Note 2: An optional loop can be passed if needed (mainly for testing)
    """
    # A coroutine is used so we can connect to the device while being inside
    # the event loop
    @asyncio.coroutine
    def _handle(loop):
        atvs = yield from pyatv.scan_for_apple_tvs(
            loop, timeout=timeout, abort_on_found=True)

        # Take the first device found
        if len(atvs) > 0:
            atv = pyatv.connect_to_apple_tv(atvs[0], loop)
            try:
                yield from handler(atv)
            finally:
                yield from atv.logout()
        else:
            if not_found is not None:
                yield from not_found()

    loop = event_loop if event_loop else asyncio.get_event_loop()
    loop.run_until_complete(_handle(loop))
