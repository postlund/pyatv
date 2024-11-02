"""Various helper methods used by test cases."""

import asyncio
from asyncio import sleep as real_sleep
from datetime import datetime
from importlib import import_module
import inspect
import os
from pathlib import Path
import time
from typing import Tuple

from aiohttp import ClientSession


# This is a special "hack" to schedule the sleep at the end of the
# event queue in order to give other possibility to run.
async def _fake_sleep(time: float = None, loop=None):
    async def dummy():
        _fake_sleep._sleep_time.insert(0, time)
        _fake_sleep._total_sleep += time

    await asyncio.ensure_future(dummy())


def stub_sleep(fn=None) -> float:
    """Stub asyncio.sleep to not make tests slow."""
    asyncio.sleep = fn or _fake_sleep

    # Code for dealing with this should be extracted
    if asyncio.sleep == _fake_sleep:
        if not hasattr(asyncio.sleep, "_sleep_time"):
            asyncio.sleep._sleep_time = [0.0]
            asyncio.sleep._total_sleep = 0.0
        if len(asyncio.sleep._sleep_time) == 1:
            return asyncio.sleep._sleep_time[0]
        return asyncio.sleep._sleep_time.pop()

    return 0.0


def unstub_sleep() -> None:
    """Restore original asyncio.sleep method."""
    if asyncio.sleep == _fake_sleep:
        asyncio.sleep._sleep_time = [0.0]
        asyncio.sleep._total_sleep = 0.0
    asyncio.sleep = real_sleep


def total_sleep_time() -> float:
    """Return total amount of fake time slept."""
    if asyncio.sleep == _fake_sleep:
        return _fake_sleep._total_sleep
    return 0.0


async def simple_get(url: str) -> Tuple[bytes, int]:
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


def data_root() -> str:
    """Return absolute path to data directory used by tests."""
    return str(Path(__file__).parent.joinpath("data"))


def data_path(filename: str) -> str:
    """Return absolute path to a test file in the data directory."""
    abs_path = str(Path(__file__).parent.joinpath("data", filename))
    if not os.path.exists(abs_path):
        raise FileNotFoundError(f"test file does not exist: {filename}")
    return abs_path


def assert_device(atv, name, address, identifier, protocol, port, creds=None):
    assert atv.name == name
    assert atv.address == address
    assert atv.identifier == identifier
    assert atv.get_service(protocol)
    assert atv.get_service(protocol).port == port
    assert atv.get_service(protocol).credentials == creds


def all_in(text: str, *strings: str) -> bool:
    """Return if all strings are in text."""
    return all(string in text for string in strings)
