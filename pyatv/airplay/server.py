"""Simple web server for serving a file to stream via AirPlay."""
import pathlib
import logging

from aiohttp import web
from aiohttp.web import middleware

from pyatv.support.net import unused_port

_LOGGER = logging.getLogger(__name__)


class StaticFileWebServer:
    """Web server serving only a single file."""

    def __init__(self, file_to_serve, address, port=None):
        """Initialize a new StaticFileWebServer."""
        self.path = pathlib.Path(file_to_serve)
        self.app = web.Application(middlewares=[self._middleware])
        self.app.router.add_static("/", self.path.parent, show_index=False)
        self.runner = web.AppRunner(self.app)
        self.site = None
        self._address = address  # Local address to bind to
        self._port = port

    async def start(self):
        """Start the web server."""
        if not self._port:
            self._port = unused_port()

        _LOGGER.debug("Starting AirPlay file server on port %d", self._port)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, str(self._address), self._port)
        await self.site.start()

    async def close(self):
        """Stop the web server and free resources."""
        _LOGGER.debug("Closing local AirPlay web server")
        await self.runner.cleanup()

    @property
    def file_address(self):
        """Address to the file being served."""
        return f"http://{self._address}:{self._port}/{self.path.name}"

    # This middleware makes sure only the specified file is accessible. This is needed
    # since aiohttp only supports serving an entire directory.
    @middleware
    async def _middleware(self, request, handler):
        if request.rel_url.path == f"/{self.path.name}":
            return await handler(request)
        return web.Response(body="Permission denied", status=401)
