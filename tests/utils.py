"""Various helper methods used by test cases."""

import time
import asyncio
import inspect

from datetime import datetime
from importlib import import_module

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


async def until(pred, timeout=5, **kwargs):
    """Wait until a predicate is fulfilled.

    Simple method of "waiting" for asynchronous code to finish.
    """
    deadline = time.time() + timeout
    while True:
        value = pred(**kwargs)
        if inspect.iscoroutinefunction(pred):
            value = await value

        if isinstance(value, tuple):
            cond, retvalue = value
            if cond:
                return retvalue
        elif value:
            return None

        if timeout is not None:
            if deadline - time.time() <= 0:
                raise asyncio.TimeoutError()

        # Use original method if stubbed
        if hasattr(asyncio, '_real_sleep'):
            await asyncio._real_sleep(0.5)
        else:
            await asyncio.sleep(0.5)


def faketime(module_name, *times):
    """Monkey patch datetime.now to return fake time."""
    class FakeDatetime:
        def __init__(self, times):
            self.times = times

        def __enter__(self):
            module = import_module(module_name)
            setattr(module.datetime, 'datetime', self)

        def __exit__(self, exc_type, exc_val, exc_tb):
            module = import_module(module_name)
            setattr(module.datetime, 'datetime', datetime)

        def now(self, tz=None):
            """Replace times from now to fake values."""
            if not self.time:
                return datetime.now(tz=tz)

            next_time = self.times[0]
            if len(self.times) > 1:
                self.times = self.times[1:]

            time = datetime.fromtimestamp(next_time)
            if tz:
                time = time.replace(tzinfo=tz)
            return time

        def __getattr__(self, attr):
            """Redirect non-stubbed functions to original module."""
            return getattr(datetime, attr)

    return FakeDatetime(list(times))
