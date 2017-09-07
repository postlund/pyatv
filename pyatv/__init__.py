"""Library for controlling an Apple TV."""

import asyncio
import logging
import concurrent
from ipaddress import ip_address

from zeroconf import ServiceBrowser, Zeroconf
from aiohttp import ClientSession

from pyatv import (convert, exceptions)
from pyatv.airplay import player
from pyatv.airplay.api import AirPlayAPI
from pyatv.const import (PROTOCOL_MRP, PROTOCOL_DMAP, PROTOCOL_AIRPLAY)
from pyatv.net import HttpSession

from pyatv.dmap.apple_tv import DmapAppleTV
from pyatv.mrp.apple_tv import MrpAppleTV

_LOGGER = logging.getLogger(__name__)


HOMESHARING_SERVICE = '_appletv-v2._tcp.local.'
DEVICE_SERVICE = '_touch-able._tcp.local.'
MEDIAREMOTE_SERVICE = '_mediaremotetv._tcp.local.'
AIRPLAY_SERVICE = '_airplay._tcp.local.'


class AppleTV:
    """Representation of an Apple TV configuration.

    An instance of this class represents a single device. A device can have
    several services, depending on the protocols it supports, e.g. DMAP or
    AirPlay.
    """

    def __init__(self, address, name):
        """Initialize a new AppleTV."""
        self.address = address
        self.name = name
        self._services = {}

    def add_service(self, service):
        """Add a new service.

        If the service already exists, it will be replaced.
        """
        if self._should_add(service):
            self._services[service.protocol] = service

    def get_service(self, protocol):
        """Look up a service based on protocol.

        If a service with the specified protocol is not available, None is
        returned.
        """
        return self._services.get(protocol, None)

    def _should_add(self, service):
        # This is a special case. Do not add a DMAP service in case it already
        # exists and have a login_id specified.
        return not (service.protocol == PROTOCOL_DMAP and
                    service.protocol in self._services and
                    not service.login_id)

    def services(self):
        """Return all supported services."""
        return list(self._services.values())

    def usable_service(self):
        """Return a usable service or None if there is none.

        A service is usable if enough configuration to be able to make a
        connection is available. If several protocols are usable, MRP will be
        preferred over DMAP.
        """
        services = self._services
        if PROTOCOL_MRP in services and services[PROTOCOL_MRP].is_usable():
            return self._services[PROTOCOL_MRP]

        if PROTOCOL_DMAP in services and services[PROTOCOL_DMAP].is_usable():
            return self._services[PROTOCOL_DMAP]

        return None

    # TODO: refactor this and usable_service
    def preferred_service(self):
        """Return the best supported service of the device.

        This methods works similarily to usable_service(), but it will return
        the most appropriate service regardless of it being usable or not. So
        an Apple TV supporting both DMAP and MRP (like gen 4) will return MRP
        here.
        """
        services = self._services
        if PROTOCOL_MRP in services and services[PROTOCOL_MRP]:
            return self._services[PROTOCOL_MRP]

        if PROTOCOL_DMAP in services and services[PROTOCOL_DMAP]:
            return self._services[PROTOCOL_DMAP]

        return None

    def is_usable(self):
        """Return True if there are any usable services."""
        return any([x.is_usable() for x in self._services.values()])

    def airplay_service(self):
        """Return service used for AirPlay.

        If no AirPlay service has been found, a default at port 7000 will be
        created.
        """
        if PROTOCOL_AIRPLAY in self._services:
            return self._services[PROTOCOL_AIRPLAY]
        return AirPlayService(7000)

    def __eq__(self, other):
        """Compare instance with another instance."""
        if isinstance(other, self.__class__):
            return self.address == other.address
        return False

    def __str__(self):
        """Return a string representation of this object."""
        services = [' - {0}'.format(s) for s in self._services.values()]
        return 'Device "{0}" at {1} supports these services:\n{2}'.format(
            self.name, self.address, '\n'.join(services))


# pylint: disable=too-few-public-methods
class BaseService:
    """Base class for protocol services."""

    def __init__(self, protocol, port):
        """Initialize a new BaseService."""
        self.protocol = protocol
        self.port = port

    @staticmethod
    def is_usable():
        """Return True if service is usable, else False."""
        return False

    def __str__(self):
        """Return a string representation of this object."""
        return 'Protocol: {0}, Port: {1}'.format(
            convert.protocol_str(self.protocol), self.port)


# pylint: disable=too-few-public-methods
class DmapService(BaseService):
    """Representation of a DMAP service."""

    def __init__(self, login_id, port=None):
        """Initialize a new DmapService."""
        super().__init__(PROTOCOL_DMAP, port or 3689)
        self.login_id = login_id

    def is_usable(self):
        """Return True if service is usable, else False."""
        return self.login_id is not None

    def __str__(self):
        """Return a string representation of this object."""
        return super().__str__() + ', Login ID: {0}'.format(self.login_id)


# pylint: disable=too-few-public-methods
class MrpService(BaseService):
    """Representation of a MediaRemote Protocol service."""

    def __init__(self, port):
        """Initialize a new MrpService."""
        super().__init__(PROTOCOL_MRP, port)

    def is_usable(self):
        """Return True if service is usable, else False."""
        return True


# pylint: disable=too-few-public-methods
class AirPlayService(BaseService):
    """Representation of an AirPlay service."""

    def __init__(self, port):
        """Initialize a new AirPlayService."""
        super().__init__(PROTOCOL_AIRPLAY, port)


class _ServiceListener(object):

    # pylint: disable=too-many-arguments
    def __init__(self, loop, abort_on_found, device_ip, protocol, semaphore):
        """Initialize a new _ServiceListener."""
        self.loop = loop
        self.abort_on_found = abort_on_found
        self.device_ip = None if not device_ip else ip_address(device_ip)
        self.protocol = protocol
        self.semaphore = semaphore
        self.found_devices = {}

    def add_service(self, zeroconf, service_type, name):
        """Handle callback from zeroconf when a service has been discovered."""
        # If it's not instantly lockable, then abort_on_found is True and we
        # have found a device already
        if self.abort_on_found and len(self.found_devices) == 1:
            return

        info = zeroconf.get_service_info(service_type, name)
        address = ip_address(info.address)

        # We might be looking for a particular device
        if self.device_ip and self.device_ip != address:
            _LOGGER.debug('Ignoring %s (not matching %s)',
                          address, self.device_ip)
            return

        if info.type == HOMESHARING_SERVICE:
            self.add_hs_service(info, address)
        elif info.type == DEVICE_SERVICE:
            self.add_non_hs_service(info, address)
        elif info.type == MEDIAREMOTE_SERVICE:
            self.add_mrp_service(info, address)
        elif info.type == AIRPLAY_SERVICE:
            self.add_airplay_service(info, address)
        else:
            _LOGGER.warning('Discovered unknown device: %s', info)

    def add_hs_service(self, info, address):
        """Add a new device to discovered list."""
        if self.protocol and self.protocol != PROTOCOL_DMAP:
            return

        name = info.properties[b'Name'].decode('utf-8')
        hsgid = info.properties[b'hG'].decode('utf-8')
        self._handle_service(address, name, DmapService(hsgid, port=info.port))

    def add_non_hs_service(self, info, address):
        """Add a new device without Home Sharing to discovered list."""
        if self.protocol and self.protocol != PROTOCOL_DMAP:
            return

        name = info.properties[b'CtlN'].decode('utf-8')
        self._handle_service(address, name, DmapService(None, port=info.port))

    def add_mrp_service(self, info, address):
        """Add a new MediaRemoteProtocol device to discovered list."""
        if self.protocol and self.protocol != PROTOCOL_MRP:
            return

        name = info.properties[b'Name'].decode('utf-8')
        self._handle_service(address, name, MrpService(info.port))

    def add_airplay_service(self, info, address):
        """Add a new AirPlay device to discovered list."""
        name = info.name.replace('._airplay._tcp.local.', '')
        self._handle_service(address, name, AirPlayService(info.port))

    def _handle_service(self, address, name, service):
        if address not in self.found_devices:
            self.found_devices[address] = AppleTV(address, name)

        _LOGGER.debug('Auto-discovered %s at %s:%d (protocol: %s)',
                      name, address, service.port, service.protocol)

        atv = self.found_devices[address]
        atv.add_service(service)

        # Check if we should continue to run or not
        if self._should_abort(address):
            _LOGGER.debug('Aborting since a device was found')

            # Only return the found device as a convenience to the user
            self.found_devices = {address: atv}

            # zeroconf is run in a different thread so this must be a
            # thread-safe call
            self.loop.call_soon_threadsafe(self.semaphore.release)

    def _should_abort(self, address):
        if not self.abort_on_found:
            return False

        return self.found_devices[address].usable_service()


# pylint: disable=too-many-arguments
@asyncio.coroutine
def scan_for_apple_tvs(loop, timeout=5, abort_on_found=False,
                       device_ip=None, only_usable=True, protocol=None):
    """Scan for Apple TVs using zeroconf (bonjour) and returns them."""
    semaphore = asyncio.Semaphore(value=0, loop=loop)
    listener = _ServiceListener(
        loop, abort_on_found, device_ip, protocol, semaphore)
    zeroconf = Zeroconf()
    try:
        ServiceBrowser(zeroconf, HOMESHARING_SERVICE, listener)
        ServiceBrowser(zeroconf, DEVICE_SERVICE, listener)
        ServiceBrowser(zeroconf, MEDIAREMOTE_SERVICE, listener)
        ServiceBrowser(zeroconf, AIRPLAY_SERVICE, listener)
        _LOGGER.debug('Discovering devices for %d seconds', timeout)
        yield from asyncio.wait_for(semaphore.acquire(), timeout, loop=loop)
    except concurrent.futures.TimeoutError:
        pass  # Will happen when timeout occurs (totally normal)
    finally:
        zeroconf.close()

    def _should_include(atv):
        if not only_usable:
            return True

        return atv.is_usable()

    return list(filter(_should_include, listener.found_devices.values()))


def connect_to_apple_tv(details, loop, protocol=None, session=None):
    """Connect and logins to an Apple TV."""
    service = _get_service_used_to_connect(details, protocol)

    # If no session is given, create a default one
    if session is None:
        session = ClientSession(loop=loop)

    # AirPlay serive is the same for both DMAP and MRP
    airplay = _setup_airplay(loop, session, details)

    # Create correct implementation depending on protocol
    if service.protocol == PROTOCOL_DMAP:
        return DmapAppleTV(loop, session, details, airplay)
    elif service.protocol == PROTOCOL_MRP:
        return MrpAppleTV(loop, session, details, airplay)


def _get_service_used_to_connect(details, protocol):
    if not protocol:
        service = details.usable_service()
    else:
        service = details.get_service(protocol)

    if not service:
        raise exceptions.NoUsableServiceError(
            'no usable service to connect to')

    return service


def _setup_airplay(loop, session, details):
    airplay_service = details.airplay_service()
    airplay_player = player.AirPlayPlayer(
        loop, session, details.address, airplay_service.port)
    airplay_http = HttpSession(
        session, 'http://{0}:{1}/'.format(
            details.address, airplay_service.port))
    return AirPlayAPI(airplay_http, airplay_player)
