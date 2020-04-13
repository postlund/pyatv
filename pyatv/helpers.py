"""Various helper methods."""

import asyncio
from typing import Callable, Optional

import pyatv


async def auto_connect(
    handler: Callable[[pyatv.interface.AppleTV], None],
    timeout: int = 5,
    not_found: Callable[[], None] = None,
    loop: Optional[asyncio.AbstractEventLoop] = None,
) -> None:
    """Connect to first discovered device.

    This is a convenience method that auto discovers devices, picks the first
    device found, connects to it and passes it to a user provided handler. An
    optional error handler can be provided that is called when no device was found.
    Very inflexible in many cases, but can be handys sometimes when trying things.

    Note: both handler and not_found must be coroutines
    """
    # Scan and do connect in the event loop
    async def _handle(loop):
        atvs = await pyatv.scan(loop, timeout=timeout)

        # Take the first device found
        if atvs:
            atv = await pyatv.connect(atvs[0], loop)

            try:
                await handler(atv)
            finally:
                atv.close()
        else:
            if not_found is not None:
                await not_found()

    loop = loop or asyncio.get_event_loop()
    await _handle(loop)
