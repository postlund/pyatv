"""Various helper methods."""

import asyncio
import pyatv


def auto_connect(handler, timeout=5, not_found=None):
    """Short method for connecting to a device.

    This is a convenience method that create an event loop, auto discovers
    devices, picks the first device found, connects to it and passes it to a
    user provided handler. An optional error handler can be provided that is
    called when no device was found. Very inflexible in many cases, but can be
    handys sometimes when trying things.

    Note: both handler and not_found must be coroutines
    """
    # A coroutine is used so we can connect to the device while being inside
    # the event loop
    async def _handle(loop):
        atvs = await pyatv.scan(loop, timeout=timeout)

        # Take the first device found
        if atvs:
            atv = await pyatv.connect(atvs[0], loop)
            try:
                await handler(atv)
            finally:
                await atv.logout()
        else:
            if not_found is not None:
                await not_found()

    loop = asyncio.get_event_loop()
    loop.run_until_complete(_handle(loop))
