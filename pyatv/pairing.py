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

PAIRING_GUID = '0000000000000001'


class PairingHandler:
    """Handle the pairing process.

    This class will publish a bonjour service and configure a webserver
    that responds to pairing requests.
    """

    def __init__(self, loop, name, pairing_code):
        """Initialize a new instance."""
        self.loop = loop
        self.name = name
        self.pairing_code = pairing_code
        self.zeroconf = Zeroconf()
        self.server = None

    @asyncio.coroutine
    def start(self):
        """Start the pairing server and publish service."""
        web_server = web.Server(self.handle_request, loop=self.loop)
        self.server = yield from self.loop.create_server(web_server, '0.0.0.0')
        allocated_port = self.server.sockets[0].getsockname()[1]
        self._setup_zeroconf(allocated_port)

    @asyncio.coroutine
    def stop(self):
        """Stop pairing server and unpublish service."""
        self.server.close()
        yield from self.server.wait_closed()
        self.zeroconf.close()

    def _setup_zeroconf(self, port):
        props = {
            'DvNm': self.name,
            'RemV': '10000',
            'DvTy': 'iPod',
            'RemN': 'Remote',
            'txtvers': '1',
            'Pair': PAIRING_GUID
            }

        local_ip = socket.inet_aton(socket.gethostbyname(socket.gethostname()))
        service = ServiceInfo('_touch-remote._tcp.local.',
                              '0'*39 + '1._touch-remote._tcp.local.',
                              local_ip, port, 0, 0, props)
        self.zeroconf.register_service(service)

    @asyncio.coroutine
    def handle_request(self, request):
        """Respond to request if PIN is correct."""
        service_name = request.rel_url.query['servicename']
        received_code = request.rel_url.query['pairingcode'].lower()
        _LOGGER.info('Got pairing request from %s with code %s',
                     service_name, received_code)

        if self._verify_pin(received_code):
            cmpg = tags.uint64_tag('cmpg', 1)
            cmnm = tags.string_tag('cmnm', self.name)
            cmty = tags.string_tag('cmty', 'ipod')
            response = tags.container_tag('cmpa', cmpg + cmnm + cmty)
            return web.Response(body=response)

        # Code did not match, generate an error
        return web.Response(status=500)

    def _verify_pin(self, received_code):
        merged = StringIO()
        merged.write(PAIRING_GUID)
        for char in str(self.pairing_code):
            merged.write(char)
            merged.write("\x00")

        expected_code = hashlib.md5(merged.getvalue().encode()).hexdigest()
        _LOGGER.debug('Got code %s, expects %s', received_code, expected_code)

        return received_code == expected_code
