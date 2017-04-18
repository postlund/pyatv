"""Various helper methods used by test cases."""

import asyncio

from aiohttp import ClientSession


@asyncio.coroutine
def simple_get(url, loop):
    """Perform a GET-request to a specified URL."""
    session = ClientSession(loop=loop)
    response = yield from session.request('GET', url)
    if response.status < 200 or response.status >= 300:
        response.close()
        session.close()
        return None, response.status

    data = yield from response.content.read()
    response.close()
    session.close()
    return data, response.status
