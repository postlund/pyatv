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
from pyatv import tags

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


class PairingHandler:
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
            cmty = tags.string_tag('cmty', 'iPhone')
            response = tags.container_tag('cmpa', cmpg + cmnm + cmty)
            self.has_paired = True
            return web.Response(body=response)

        # Code did not match, generate an error
        return web.Response(status=500)

    def _verify_pin(self, received_code):
        # If no particular pin code is specified, allow any pin
        if self.pin_code is None:
            return True

        merged = StringIO()
        merged.write(self.pairing_guid)
        for char in str(self.pin_code).zfill(4):
            merged.write(char)
            merged.write("\x00")

        expected_code = hashlib.md5(merged.getvalue().encode()).hexdigest()
        _LOGGER.debug('Got code %s, expects %s', received_code, expected_code)

        return received_code == expected_code
