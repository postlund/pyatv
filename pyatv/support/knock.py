"""Module used to knock on TCP ports.

This module will open a TCP-connection to one or more ports on a given host and
immediately close it. The use case for this is to wake a device sleeping via a Bonjour
sleep proxy. Such a device will automatically be woken up in case any of its services
are accessed, something this module will try to emulate.
"""

import math
import socket
import select
import asyncio
import logging

from typing import List
from ipaddress import IPv4Address

_LOGGER = logging.getLogger(__name__)

SEND_INTERVAL = 2.0


# Performs the actual "knock". This can most certainly be done with asyncio code, but
# works for now.
def _synch_knock(address: IPv4Address, port: int):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setblocking(False)

    socket_address = (str(address), port)
    s.connect_ex(socket_address)
    select.select([s], [s], [s], 0.1)
    s.close()


async def knock(
    address: IPv4Address, ports: List[int], loop: asyncio.AbstractEventLoop
):
    """Knock on a set of ports for a given host."""
    _LOGGER.debug("Knocking at ports %s on %s", ports, address)
    await asyncio.wait(
        [loop.run_in_executor(None, _synch_knock, address, port) for port in ports]
    )


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
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("failed to port knock")
            await asyncio.sleep(SEND_INTERVAL)

    return asyncio.ensure_future(_repeat())
