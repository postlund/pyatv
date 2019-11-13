"""Library for controlling an Apple TV."""

import asyncio
import logging
from ipaddress import ip_address

from aiozeroconf import ServiceBrowser, Zeroconf

from pyatv import (conf, const, exceptions, net)
from pyatv.airplay import player
from pyatv.airplay import AirPlayAPI
from pyatv.net import HttpSession

from pyatv.dmap import DmapAppleTV
from pyatv.dmap.pairing import DmapPairingHandler
from pyatv.mrp import MrpAppleTV
from pyatv.mrp.pairing import MrpPairingHandler
from pyatv.airplay.pairing import AirPlayPairingHandler


_LOGGER = logging.getLogger(__name__)

HOMESHARING_SERVICE = '_appletv-v2._tcp.local.'
DEVICE_SERVICE = '_touch-able._tcp.local.'
MEDIAREMOTE_SERVICE = '_mediaremotetv._tcp.local.'
AIRPLAY_SERVICE = '_airplay._tcp.local.'


def _zcprop(info, prop):
    value = info.properties.get(prop.encode('utf-8'), None)
    if value:
        return value.decode('utf-8')
    return None


class _ServiceListener:

    def __init__(self, loop):
        """Initialize a new _ServiceListener."""
        self.loop = loop
        self.found_devices = {}

    def add_service(self, zeroconf, service_type, name):
        """Handle callback from zeroconf when a service has been discovered."""
        asyncio.ensure_future(self._internal_add(zeroconf, service_type, name))

    def remove_service(self, zeroconf, service_type, name):
        """Handle callback when a service is removed."""

    async def _internal_add(self, zeroconf, service_type, name):
        info = await zeroconf.get_service_info(
            service_type, name, timeout=2000)
        if info.address is None:
            _LOGGER.warning("Failed to resolve %s (%s)", service_type, name)
            return

        address = ip_address(info.address)

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
        identifier = info.name.split('.')[0]
        name = _zcprop(info, 'Name')
        hsgid = _zcprop(info, 'hG')
        service = conf.DmapService(identifier, hsgid, port=info.port)
        self._handle_service(address, name, service)

    def add_non_hs_service(self, info, address):
        """Add a new device without Home Sharing to discovered list."""
        identifier = info.name.split('.')[0]
        name = _zcprop(info, 'CtlN')
        service = conf.DmapService(identifier, None, port=info.port)
        self._handle_service(address, name, service)

    def add_mrp_service(self, info, address):
        """Add a new MediaRemoteProtocol device to discovered list."""
        identifier = _zcprop(info, 'UniqueIdentifier')
        name = _zcprop(info, 'Name')
        service = conf.MrpService(identifier, info.port)
        self._handle_service(address, name, service)

    def add_airplay_service(self, info, address):
        """Add a new AirPlay device to discovered list."""
        identifier = _zcprop(info, 'deviceid')
        name = info.name.replace('.' + AIRPLAY_SERVICE, '')
        service = conf.AirPlayService(identifier, info.port)
        self._handle_service(address, name, service)

    def _handle_service(self, address, name, service):
        if address not in self.found_devices:
            self.found_devices[address] = conf.AppleTV(address, name)

        _LOGGER.debug('Auto-discovered %s at %s:%d (protocol: %s)',
                      name, address, service.port, service.protocol)

        atv = self.found_devices[address]
        atv.add_service(service)


async def scan(loop, timeout=5, identifier=None, protocol=None):
    """Scan for Apple TVs using zeroconf (bonjour) and returns them."""
    listener = _ServiceListener(loop)
    zeroconf = Zeroconf(loop)
    try:
        ServiceBrowser(zeroconf, HOMESHARING_SERVICE, listener)
        ServiceBrowser(zeroconf, DEVICE_SERVICE, listener)
        ServiceBrowser(zeroconf, MEDIAREMOTE_SERVICE, listener)
        ServiceBrowser(zeroconf, AIRPLAY_SERVICE, listener)
        _LOGGER.debug('Discovering devices for %d seconds', timeout)
        await asyncio.sleep(timeout)
    finally:
        await zeroconf.close()

    def _should_include(atv):
        if identifier and identifier not in atv.all_identifiers:
            return False

        if protocol and atv.get_service(protocol) is None:
            return False

        return True

    found_devices = listener.found_devices.values()
    return [x for x in found_devices if _should_include(x)]


async def connect(config, loop, protocol=None, session=None):
    """Connect and logins to an Apple TV."""
    if config.identifier is None:
        raise exceptions.DeviceIdMissingError("no device identifier")

    service = config.main_service(protocol=protocol)

    supported_implementations = {
        const.PROTOCOL_DMAP: DmapAppleTV,
        const.PROTOCOL_MRP: MrpAppleTV,
    }

    implementation = supported_implementations.get(service.protocol, None)
    if not implementation:
        raise exceptions.UnsupportedProtocolError()

    # If no session is given, create a default one
    if session is None:
        session = await net.create_session(loop=loop)

    # AirPlay service is the same for both DMAP and MRP
    airplay = _setup_airplay(loop, session, config)

    atv = implementation(loop, session, config, airplay)
    await atv.connect()
    return atv


def _setup_airplay(loop, session, config):
    airplay_service = config.get_service(const.PROTOCOL_AIRPLAY)
    airplay_player = player.AirPlayPlayer(
        loop, session, config.address, airplay_service.port)
    airplay_http = HttpSession(
        session, 'http://{0}:{1}/'.format(
            config.address, airplay_service.port))
    return AirPlayAPI(config, airplay_http, airplay_player)


async def pair(config, protocol, loop, session=None, **kwargs):
    """Pair with an Apple TV."""
    service = config.get_service(protocol)
    if not service:
        raise exceptions.NoServiceError(
            'no service available for protocol ' + str(protocol))

    protocol_handlers = {
        const.PROTOCOL_DMAP: DmapPairingHandler,
        const.PROTOCOL_MRP: MrpPairingHandler,
        const.PROTOCOL_AIRPLAY: AirPlayPairingHandler,
    }

    handler = protocol_handlers.get(protocol, None)
    if handler is None:
        raise exceptions.UnsupportedProtocolError()

    if session is None:
        session = await net.create_session(loop)

    return handler(config, session, loop, **kwargs)
