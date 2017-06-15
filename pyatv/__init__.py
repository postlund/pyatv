"""Library for controlling an Apple TV."""

import asyncio
import logging
import concurrent
import ipaddress

from collections import namedtuple
from zeroconf import ServiceBrowser, Zeroconf
from aiohttp import ClientSession

from pyatv.pairing import PairingHandler
from pyatv.internal.apple_tv import AppleTVInternal

_LOGGER = logging.getLogger(__name__)


HOMESHARING_SERVICE = '_appletv-v2._tcp.local.'
DEVICE_SERVICE = '_touch-able._tcp.local.'


class AppleTVDevice(
        namedtuple('AppleTVDevice',
                   'name, address, login_id, port, airplay_port')):
    """Representation of an Apple TV device used when connecting."""

    # pylint: disable=too-many-arguments
    def __new__(cls, name, address, login_id, port=3689, airplay_port=7000):
        """Initialize a new AppleTVDevice."""
        return super(AppleTVDevice, cls).__new__(
            cls, name, address, login_id, port, airplay_port)


# pylint: disable=too-few-public-methods
class _ServiceListener(object):

    def __init__(self, abort_on_found, semaphore):
        """Initialize a new _ServiceListener."""
        self.abort_on_found = abort_on_found
        self.semaphore = semaphore
        self.found_devices = {}

    def add_service(self, zeroconf, service_type, name):
        """Handle callback from zeroconf when a service has been discovered."""
        # If it's not instantly lockable, then abort_on_found is True and we
        # have found a device already
        if not self.semaphore.locked():
            return

        info = zeroconf.get_service_info(service_type, name)
        if info.type == HOMESHARING_SERVICE:
            self.add_hs_device(info)

            # Check if we should continue to run or not
            if self.abort_on_found:
                _LOGGER.debug('Aborting since a device was found')
                self.semaphore.release()
        elif info.type == DEVICE_SERVICE:
            self.add_device(info)
        else:
            _LOGGER.warning('Discovered unknown device: %s', info)

    def add_hs_device(self, info):
        """Add a new device to discovered list."""
        address = ipaddress.ip_address(info.address)
        tv_name = info.properties[b'Name'].decode('utf-8')
        hsgid = info.properties[b'hG'].decode('utf-8')
        self.found_devices[address] = AppleTVDevice(tv_name, address, hsgid)
        _LOGGER.debug('Auto-discovered service %s at %s (hsgid: %s)',
                      tv_name, address, hsgid)

    def add_device(self, info):
        """Add a new device without Home Sharing to discovered list."""
        address = ipaddress.ip_address(info.address)
        tv_name = info.properties[b'CtlN'].decode('utf-8')
        if address not in self.found_devices:
            self.found_devices[address] = AppleTVDevice(tv_name, address, None)
            _LOGGER.debug('Auto-discovered service %s at %s (no home sharing)',
                          tv_name, address)
        else:
            _LOGGER.debug('Ignoring %s since its already known with HSGID',
                          address)


@asyncio.coroutine
def scan_for_apple_tvs(loop, timeout=5,
                       abort_on_found=False, only_home_sharing=True):
    """Scan for Apple TVs using zeroconf (bonjour) and returns them."""
    semaphore = asyncio.Semaphore(value=0, loop=loop)
    listener = _ServiceListener(abort_on_found, semaphore)
    zeroconf = Zeroconf()
    try:
        ServiceBrowser(zeroconf, HOMESHARING_SERVICE, listener)
        ServiceBrowser(zeroconf, DEVICE_SERVICE, listener)
        _LOGGER.debug('Discovering devices for %d seconds', timeout)
        yield from asyncio.wait_for(semaphore.acquire(), timeout, loop=loop)
    except concurrent.futures.TimeoutError:
        pass  # Will happen when timeout occurs (totally normal)
    finally:
        zeroconf.close()

    def _should_include(atv):
        if not only_home_sharing:
            return True

        return atv.login_id is not None

    return list(filter(_should_include, listener.found_devices.values()))


def connect_to_apple_tv(details, loop, session=None):
    """Connect and logins to an Apple TV."""
    # If no session is given, create a default one
    if session is None:
        session = ClientSession(loop=loop)

    # If/when needed, the library should figure out the correct type of Apple
    # TV and return the correct type for it.
    return AppleTVInternal(loop, session, details)


def pair_with_apple_tv(loop, pin_code, name, pairing_guid=None):
    """Initialize pairing process with an Apple TV."""
    return PairingHandler(loop, name, pin_code, pairing_guid=pairing_guid)
