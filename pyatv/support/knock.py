"""Module used to knock on TCP ports.

This module will open a TCP-connection to one or more ports on a given host and
immediately close it. The use case for this is to wake a device sleeping via a Bonjour
sleep proxy. Such a device will automatically be woken up in case any of its services
are accessed, something this module will try to emulate.
"""

import asyncio
import contextlib
from ipaddress import IPv4Address
import logging
import math
import socket
from typing import List

_LOGGER = logging.getLogger(__name__)

SEND_INTERVAL = 2.0


async def _async_knock(address: IPv4Address, port: int):
    """Open a connection to the device to wake a given host."""
    with contextlib.suppress(
        (OSError, BlockingIOError, InterruptedError)
    ), socket.socket(socket.AF_INET, socket.SOCK_STREAM) as knock_sock:
        knock_sock.setblocking(False)  # must be non-blocking for async
        knock_sock.connect((str(address), port))
        await asyncio.sleep(0.1)


async def knock(
    address: IPv4Address, ports: List[int], loop: asyncio.AbstractEventLoop
):
    """Knock on a set of ports for a given host."""
    _LOGGER.debug("Knocking at ports %s on %s", ports, address)
    for port in ports:
        # Do one at a time so we yield to the event loop between connect() calls
        await _async_knock(address, port)


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
    no_of_sends = math.ceil(timeout / SEND_INTERVAL)

    async def _repeat():
        for _ in range(no_of_sends):
            try:
                await knock(address, ports, loop)
                await asyncio.sleep(SEND_INTERVAL)
            except asyncio.CancelledError:
                break
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("failed to port knock")

    return asyncio.ensure_future(_repeat())
