"""Module used to knock on TCP ports.

This module will open a TCP-connection to one or more ports on a given host and
immediately close it. The use case for this is to wake a device sleeping via a Bonjour
sleep proxy. Such a device will automatically be woken up in case any of its services
are accessed, something this module will try to emulate.
"""

import asyncio
import errno
from ipaddress import IPv4Address
import logging
from typing import List

_LOGGER = logging.getLogger(__name__)

_ABORT_KNOCK_ERRNOS = {errno.EHOSTDOWN, errno.EHOSTUNREACH}


async def _async_knock(address: IPv4Address, port: int, sleep_time: float) -> None:
    """Open a connection to the device to wake a given host."""
    try:
        _, writer = await asyncio.open_connection(str(address), port)
    except asyncio.CancelledError:
        pass
    except OSError as ex:
        if ex.errno in _ABORT_KNOCK_ERRNOS:
            return False
    else:
        await asyncio.sleep(sleep_time)
        writer.close()
    return True


async def knock(address: IPv4Address, ports: List[int], timeout: float) -> None:
    """Knock on a set of ports for a given host."""
    _LOGGER.debug("Knocking at ports %s on %s", ports, address)
    sleep_time = (len(ports) / timeout) - 0.1
    for port in ports:
        if not await _async_knock(address, port, sleep_time):
            # If the host host is down don't try the other ports
            return


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
