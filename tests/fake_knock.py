import asyncio
import logging

import pytest

_LOGGER = logging.getLogger(__name__)


class KnockServer(asyncio.Protocol):
    def __init__(self, port):
        self.got_knock = False
        self.count = 0
        self.port = port

    def connection_made(self, transport):
        own = transport.get_extra_info("sockname")
        peername = transport.get_extra_info("peername")
        _LOGGER.debug("Knock on %s:%d from %s:%d", *own, *peername)
        self.transport = transport

    def connection_lost(self, exc):
        self.got_knock = True
        self.count += 1
        self.transport = None

    def data_received(self, data):
        assert False, "no data shall be received"


async def create_knock_server(port, loop):
    server = KnockServer(port)
    return await loop.create_server(lambda: server, "127.0.0.1", port), server
