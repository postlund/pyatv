"""Various helper methods used by test cases."""

import asyncio

from aiohttp import ClientSession


@asyncio.coroutine
def simple_get(testcase, url, loop):
    """Perform a GET-request to a specified URL."""
    session = ClientSession(loop=loop)
    response = yield from session.request('GET', url)
    testcase.assertEqual(response.status, 200,
                         msg='request to {0} failed'.format(url))
    data = yield from response.content.read()
    response.close()
    yield from session.close()
    return data
