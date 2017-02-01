"""Library for controlling an Apple TV."""

import asyncio
import logging

import ipaddress
from collections import namedtuple
from zeroconf import ServiceBrowser, Zeroconf

from pyatv.daap import (DaapSession, DaapRequester)
from pyatv.internal.apple_tv import AppleTVInternal

_LOGGER = logging.getLogger(__name__)

HOMESHARING_SERVICE = '_appletv-v2._tcp.local.'


class AppleTVDevice(namedtuple('AppleTVDevice', 'name, address, hsgid, port')):
    """Representation of an Apple TV device used when connecting."""

    def __new__(cls, name, address, hsgid, port=3689):
        """"Initialize a new AppleTVDevice."""
        return super(AppleTVDevice, cls).__new__(
            cls, name, address, hsgid, port)


# pylint: disable=too-few-public-methods
class _ServiceListener(object):

    def __init__(self):
        """Initialize a new _ServiceListener."""
        self.found_devices = []

    def add_service(self, zeroconf, service_type, name):
        """Callback from zeroconf when a service has been discovered."""
        info = zeroconf.get_service_info(service_type, name)
        if info.type == HOMESHARING_SERVICE:
            address = ipaddress.ip_address(info.address)
            tv_name = info.properties[b'Name'].decode('utf-8')
            hsgid = info.properties[b'hG'].decode('utf-8')
            self.found_devices.append(AppleTVDevice(tv_name, address, hsgid))
            _LOGGER.debug('Auto-discovered service %s at %s (hsgid: %s)',
                          tv_name, address, hsgid)
        else:
            _LOGGER.warning('Discovered unknown device: %s', info)


@asyncio.coroutine
def scan_for_apple_tvs(timeout=5):
    """Scan for Apple TVs using zeroconf (bonjour) and returns them."""
    listener = _ServiceListener()
    zeroconf = Zeroconf()
    try:
        ServiceBrowser(zeroconf, HOMESHARING_SERVICE, listener)
        _LOGGER.debug('Discovering devices for %d seconds', timeout)
        yield from asyncio.sleep(timeout)
    finally:
        zeroconf.close()

    return listener.found_devices


def connect_to_apple_tv(details, loop):
    """Connect and logins to an Apple TV."""
    # If/when needed, the library should figure out the correct type of Apple
    # TV and return the correct type for it.
    session = DaapSession(loop)
    requester = DaapRequester(
        session, details.address, details.hsgid, details.port)
    return AppleTVInternal(session, requester)


# TODO: API not determined for this yet, might change when implemented
def pair_with_apple_tv():
    """Initiate pairing process with an Apple TV."""
    raise NotImplementedError
