"""Various helper methods used by test cases."""

import time
import asyncio
from aiohttp import ClientSession


def stub_sleep():
    """Stub asyncio.sleep and keep reference to real sleep.

    The tests should not sleep as that makes them slow, but the until function
    below must be able to do so (as it is polling). This method makes sure we
    still have a reference to original sleep in test environment.

    Calling this function stubs asyncio.sleep globally, so technically it only
    needs to be called once.
    """
    if not hasattr(asyncio, '_real_sleep'):
        # This is a special "hack" to schedule the sleep at the end of the
        # event queue in order to give other possibility to run.
        async def fake_sleep(time=None, loop=None):
            async def dummy():
                pass
            await asyncio.ensure_future(dummy())
        asyncio._real_sleep = asyncio.sleep
        asyncio.sleep = fake_sleep


async def simple_get(url):
    """Perform a GET-request to a specified URL."""
    session = ClientSession()
    response = await session.request('GET', url)
    if response.status < 200 or response.status >= 300:
        response.close()
        await session.close()
        return None, response.status

    data = await response.content.read()
    response.close()
    await session.close()
    return data, response.status


# This is a modified version of run_until from uvloop:
# https://github.com/MagicStack/uvloop/blob/176569118e4dfd520ee9c1b87edb08ba16d13a83/uvloop/_testbase.py#L535  # noqa
async def until(pred, timeout=20):
    """Wait until a predicate is fulfilled.

    Simple method of "waiting" for asynchronous code to finish.
    """
    deadline = time.time() + timeout
    while not pred():
        if timeout is not None:
            if deadline - time.time() <= 0:
                raise asyncio.futures.TimeoutError()

        # Use original method if stubbed
        if hasattr(asyncio, '_real_sleep'):
            await asyncio._real_sleep(0.5)
        else:
            await asyncio.sleep(0.5)
