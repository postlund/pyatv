"""Module used for pairing pyatv with a device."""

import socket
import asyncio
import hashlib
import logging
import random
from io import StringIO

from aiohttp import web
from zeroconf import ServiceInfo
from pyatv import tags

_LOGGER = logging.getLogger(__name__)

DEFAULT_PAIRING_GUID = '0000000000000001'


class PairingHandler(object):
    """Handle the pairing process.

    This class will publish a bonjour service and configure a webserver
    that responds to pairing requests.
    """

    def __init__(self, loop, name, pin_code, pairing_guid=None):
        """Initialize a new instance."""
        self._loop = loop
        self._name = name
        self._web_server = None
        self._server = None
        self.pin_code = pin_code
        self.pairing_guid = pairing_guid or self._generate_random_guid()
        self.has_paired = False

    @staticmethod
    def _generate_random_guid():
        return hex(random.getrandbits(64))[2:].upper()  # Remove leading 0x

    @asyncio.coroutine
    def start(self, zeroconf):
        """Start the pairing server and publish service."""
        self._web_server = web.Server(self.handle_request, loop=self._loop)
        self._server = yield from self._loop.create_server(
            self._web_server, '0.0.0.0')

        # Get the allocated (random port) and include it in zeroconf service
        allocated_port = self._server.sockets[0].getsockname()[1]
        _LOGGER.debug('Started pairing web server at port %d', allocated_port)

        self._setup_zeroconf(zeroconf, allocated_port)

    @asyncio.coroutine
    def stop(self):
        """Stop pairing server and unpublish service."""
        _LOGGER.debug('Shutting down pairing server')
        if self._web_server is not None:
            yield from self._web_server.shutdown()
            self._server.close()

        if self._server is not None:
            yield from self._server.wait_closed()

    def _setup_zeroconf(self, zeroconf, port):
        props = {
            b'DvNm': self._name,
            b'RemV': b'10000',
            b'DvTy': b'iPod',
            b'RemN': b'Remote',
            b'txtvers': b'1',
            b'Pair': self.pairing_guid
            }

        local_ip = socket.inet_aton(socket.gethostbyname(socket.gethostname()))
        service = ServiceInfo('_touch-remote._tcp.local.',
                              '0'*39 + '1._touch-remote._tcp.local.',
                              local_ip, port, 0, 0, props)
        zeroconf.register_service(service)

        _LOGGER.debug('Published zeroconf service: %s', service)

    @asyncio.coroutine
    def handle_request(self, request):
        """Respond to request if PIN is correct."""
        service_name = request.rel_url.query['servicename']
        received_code = request.rel_url.query['pairingcode'].lower()
        _LOGGER.info('Got pairing request from %s with code %s',
                     service_name, received_code)

        if self._verify_pin(received_code):
            cmpg = tags.uint64_tag('cmpg', int(self.pairing_guid, 16))
            cmnm = tags.string_tag('cmnm', self._name)
            cmty = tags.string_tag('cmty', 'ipod')
            response = tags.container_tag('cmpa', cmpg + cmnm + cmty)
            self.has_paired = True
            return web.Response(body=response)

        # Code did not match, generate an error
        return web.Response(status=500)

    def _verify_pin(self, received_code):
        merged = StringIO()
        merged.write(self.pairing_guid)
        for char in str(self.pin_code):
            merged.write(char)
            merged.write("\x00")

        expected_code = hashlib.md5(merged.getvalue().encode()).hexdigest()
        _LOGGER.debug('Got code %s, expects %s', received_code, expected_code)

        return received_code == expected_code
