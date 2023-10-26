"""Module used to knock on TCP ports.

This module will open a TCP-connection to one or more ports on a given host and
immediately close it. The use case for this is to wake a device sleeping via a Bonjour
sleep proxy. Such a device will automatically be woken up in case any of its services
are accessed, something this module will try to emulate.
"""

import asyncio
from asyncio.tasks import FIRST_EXCEPTION
import errno
from ipaddress import IPv4Address
import logging
from typing import List

_LOGGER = logging.getLogger(__name__)

_ABORT_KNOCK_ERRNOS = {errno.EHOSTDOWN, errno.EHOSTUNREACH}

_SLEEP_AFTER_CONNECT = 0.1
_KNOCK_TIMEOUT_BUFFER = _SLEEP_AFTER_CONNECT * 2


async def _async_knock(address: IPv4Address, port: int, timeout: float) -> None:
    """Open a connection to the device to wake a given host."""
    writer = None
    try:
        _, writer = await asyncio.wait_for(
            asyncio.open_connection(str(address), port), timeout=timeout
        )
    except asyncio.TimeoutError:
        pass
    except OSError as ex:
        # If we get EHOSTDOWN or EHOSTUNREACH we
        # can give up as its not going to wake
        # a device that is not there
        if ex.errno in _ABORT_KNOCK_ERRNOS:
            raise
    else:
        await asyncio.sleep(_SLEEP_AFTER_CONNECT)
    finally:
        if writer:
            writer.close()


async def knock(address: IPv4Address, ports: List[int], timeout: float) -> None:
    """Knock on a set of ports for a given host."""
    tasks = []
    knock_runtime = timeout - _KNOCK_TIMEOUT_BUFFER
    for port in ports:
        # yield to the event loop to ensure we do not block
        await asyncio.sleep(0)
        _LOGGER.debug("Knocking at port %s on %s", port, address)
        tasks.append(
            asyncio.ensure_future(
                asyncio.create_task(_async_knock(address, port, knock_runtime))
            )
        )
    _, pending = await asyncio.wait(tasks, return_when=FIRST_EXCEPTION)
    if pending:
        for task in pending:
            task.cancel()
        for result in await asyncio.gather(*pending, return_exceptions=True):
            if isinstance(result, Exception) and not isinstance(result, OSError):
                raise result


async def knocker(
    address: IPv4Address,
    ports: List[int],
    loop: asyncio.AbstractEventLoop,
    timeout: int = 4,
) -> asyncio.Future:
    """Continuously knock on a set of ports.

    New port knocks are sent every two seconds, so a timeout of 4 seconds will result in
    two knocks.
    """
    return asyncio.ensure_future(knock(address, ports, timeout))
