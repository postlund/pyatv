"""Module used for pairing pyatv with a device."""

import socket
import asyncio
import hashlib
import logging
from io import StringIO

from aiohttp import web
from zeroconf import Zeroconf, ServiceInfo
from pyatv import tags

_LOGGER = logging.getLogger(__name__)

PAIR = '0000000000000001'


class PairingHandler:
    """Handle the pairing process.

    This class will publish a bonjour service and configure a webserver
    that responds to pairing requests.
    """

    def __init__(self, loop, timeout, name, pairing_code):
        """Initialize a new instance."""
        self.loop = loop
        self.timeout = timeout
        self.name = name
        self.pairing_code = pairing_code
        self.zeroconf = Zeroconf()

    @asyncio.coroutine
    def run(self):
        """Start the pairing server and publish service."""
        web_server = web.Server(self.handle_request, loop=self.loop)
        server = yield from self.loop.create_server(web_server, '0.0.0.0')
        allocated_port = server.sockets[0].getsockname()[1]
        service = self._setup_zeroconf(allocated_port)
        print("lol: " + str(self.zeroconf))
        print("timeout: " + str(self.timeout))
        try:
            yield from asyncio.sleep(self.timeout, loop=self.loop)
        finally:
            # TODO: should close here but that makes it hard to test
            # Use have a stop method instead?
            # server.close()
            self.zeroconf.unregister_service(service)
            self.zeroconf.close()

    def _setup_zeroconf(self, port):
        props = {
            'DvNm': self.name,
            'RemV': '10000',
            'DvTy': 'iPod',
            'RemN': 'Remote',
            'txtvers': '1',
            'Pair': PAIR
            }

        local_ip = socket.inet_aton(socket.gethostbyname(socket.gethostname()))
        service = ServiceInfo('_touch-remote._tcp.local.',
                              '0'*39 + '1._touch-remote._tcp.local.',
                              local_ip, port, 0, 0, props)
        self.zeroconf.register_service(service)
        return service

    @asyncio.coroutine
    def handle_request(self, request):
        """Respond to request if PIN is correct."""
        received_code = request.rel_url.query['pairingcode'].lower()

        if self._verify_pin(received_code):
            cmpg = tags.uint64_tag('cmpg', 1)
            cmnm = tags.string_tag('cmnm', self.name)
            cmty = tags.string_tag('cmty', 'ipod')
            response = tags.container_tag('cmpa', cmpg + cmnm + cmty)
            # TODO: take down web server and cancel delay when done?
            return web.Response(body=response)

        # Code did not match, generate an error
        return web.Response(status=500)

    def _verify_pin(self, received_code):
        merged = StringIO()
        merged.write(PAIR)
        for char in str(self.pairing_code):
            merged.write(char)
            merged.write("\x00")

        expected_code = hashlib.md5(merged.getvalue().encode()).hexdigest()
        _LOGGER.debug('Got code %s, expects %s', received_code, expected_code)

        return received_code == expected_code
