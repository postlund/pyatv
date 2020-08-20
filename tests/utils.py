"""Various helper methods used by test cases."""

import time
import asyncio
import inspect

from datetime import datetime
from importlib import import_module
from asyncio import sleep as real_sleep

from aiohttp import ClientSession


# This is a special "hack" to schedule the sleep at the end of the
# event queue in order to give other possibility to run.
async def _fake_sleep(time: float = None, loop=None):
    async def dummy():
        _fake_sleep._sleep_time.insert(0, time)

    await asyncio.ensure_future(dummy())


def stub_sleep(fn=None) -> float:
    """Stub asyncio.sleep to not make tests slow."""
    asyncio.sleep = fn or _fake_sleep

    # Code for dealing with this should be extracted
    if asyncio.sleep == _fake_sleep:
        if not hasattr(asyncio.sleep, "_sleep_time"):
            asyncio.sleep._sleep_time = [0.0]
        if len(asyncio.sleep._sleep_time) == 1:
            return asyncio.sleep._sleep_time[0]
        return asyncio.sleep._sleep_time.pop()

    return 0.0


def unstub_sleep():
    """Restore original asyncio.sleep method."""
    if asyncio.sleep == _fake_sleep:
        asyncio.sleep._sleep_time = [0.0]
    asyncio.sleep = real_sleep


async def simple_get(url):
    """Perform a GET-request to a specified URL."""
    async with ClientSession() as session:
        async with session.get(url) as response:

            if response.status < 200 or response.status >= 300:
                return None, response.status

            data = None
            data = await response.content.read()
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

        await real_sleep(0.01)


def faketime(module_name, *times):
    """Monkey patch datetime.now to return fake time."""

    class FakeDatetime:
        def __init__(self, times):
            self.times = times

        def __enter__(self):
            module = import_module(module_name)
            setattr(module.datetime, "datetime", self)

        def __exit__(self, exc_type, exc_val, exc_tb):
            module = import_module(module_name)
            setattr(module.datetime, "datetime", datetime)

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

        def __call__(self, *args, **kwargs):
            return datetime(*args, **kwargs)

        def __getattr__(self, attr):
            """Redirect non-stubbed functions to original module."""
            return getattr(datetime, attr)

    return FakeDatetime(list(times))
