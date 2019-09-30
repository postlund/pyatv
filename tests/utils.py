"""Various helper methods used by test cases."""

from aiohttp import ClientSession


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
