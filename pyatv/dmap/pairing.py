"""Module used for pairing pyatv with a device."""

import socket
import asyncio
import hashlib
import logging
import random
import ipaddress
from io import StringIO

from aiohttp import web
from zeroconf import ServiceInfo
import netifaces

from pyatv.dmap import tags
from pyatv.interface import PairingHandler

_LOGGER = logging.getLogger(__name__)

DEFAULT_PAIRING_GUID = '0000000000000001'


# TODO: netifaces is written in C and pylint does not find members
# of that library correctly. Maybe there is a solution to this?
# pylint: disable=no-member
def _get_private_ip_addresses():
    for iface in netifaces.interfaces():
        addresses = netifaces.ifaddresses(iface)
        if netifaces.AF_INET not in addresses:
            continue

        for addr in addresses[netifaces.AF_INET]:
            ipaddr = ipaddress.ip_address(addr['addr'])
            if ipaddr.is_private and not ipaddr.is_loopback:
                yield ipaddr


class DmapPairingHandler(PairingHandler):
    """Handle the pairing process.

    This class will publish a bonjour service and configure a webserver
    that responds to pairing requests.
    """

    def __init__(self, loop):
        """Initialize a new instance."""
        self._loop = loop
        self._name = None
        self._web_server = None
        self._server = None
        self.pin_code = None
        self.pairing_guid = None
        self._has_paired = False

    @staticmethod
    def _generate_random_guid():
        return hex(random.getrandbits(64))[2:].upper()  # Remove leading 0x

    @property
    def has_paired(self):
        """If a successful pairing has been performed.

        The value will be reset when stop() is called.
        """
        return self._has_paired

    @asyncio.coroutine
    def start(self, **kwargs):
        """Start the pairing server and publish service."""
        zeroconf = kwargs['zeroconf']
        self._name = kwargs['name']
        self.pin_code = kwargs['pin']
        self._web_server = web.Server(self.handle_request, loop=self._loop)
        self._server = yield from self._loop.create_server(
            self._web_server, '0.0.0.0')

        # Get the allocated (random port) and include it in zeroconf service
        allocated_port = self._server.sockets[0].getsockname()[1]
        _LOGGER.debug('Started pairing web server at port %d', allocated_port)

        self._setup_zeroconf(zeroconf, allocated_port)

    @asyncio.coroutine
    def stop(self, **kwargs):
        """Stop pairing server and unpublish service."""
        _LOGGER.debug('Shutting down pairing server')
        self._has_paired = False
        if self._web_server is not None:
            yield from self._web_server.shutdown()
            self._server.close()

        if self._server is not None:
            yield from self._server.wait_closed()

    @asyncio.coroutine
    def set(self, key, value, **kwargs):
        """Set a process specific value.

        The value is specific to the device being paired with and can for
        instance be a PIN code.
        """
        if key == 'pairing_guid':
            self.pairing_guid = value or self._generate_random_guid()

    @asyncio.coroutine
    def get(self, key):
        """Retrieve a process specific value."""
        if key == 'pairing_guid':
            return self.pairing_guid

        return None

    def _publish_service(self, zeroconf, address, port):
        props = {
            b'DvNm': self._name,
            b'RemV': b'10000',
            b'DvTy': b'iPod',
            b'RemN': b'Remote',
            b'txtvers': b'1',
            b'Pair': self.pairing_guid
            }

        service = ServiceInfo(
            '_touch-remote._tcp.local.',
            '{0:040d}._touch-remote._tcp.local.'.format(int(address)),
            socket.inet_aton(str(address)), port, 0, 0, props)
        zeroconf.register_service(service)

        _LOGGER.debug('Published zeroconf service: %s', service)

    def _setup_zeroconf(self, zeroconf, port):
        for ipaddr in _get_private_ip_addresses():
            self._publish_service(zeroconf, ipaddr, port)

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
            self._has_paired = True
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
