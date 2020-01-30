"""Library for controlling an Apple TV."""

import os
import asyncio
import logging
import datetime  # noqa
from ipaddress import ip_address

from aiozeroconf import ServiceBrowser, Zeroconf
import netifaces

from pyatv import (conf, exceptions, net, udns)
from pyatv.airplay import AirPlayStreamAPI
from pyatv.const import Protocol
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

ALL_SERVICES = [
    HOMESHARING_SERVICE,
    DEVICE_SERVICE,
    MEDIAREMOTE_SERVICE,
    AIRPLAY_SERVICE
]


def _property_decode(properties, prop):
    value = properties.get(prop.encode('utf-8'))
    if value:
        return value.decode('utf-8')
    return None


class BaseScanner:  # pylint: disable=too-few-public-methods
    """Base scanner for service discovery."""

    def __init__(self):
        """Initialize a new BaseScanner."""
        self._found_devices = {}

    def service_discovered(  # pylint: disable=too-many-arguments
            self, service_type, service_name, address, port, properties):
        """Call when a service was discovered."""
        supported_types = {
            HOMESHARING_SERVICE: self._hs_service,
            DEVICE_SERVICE: self._non_hs_service,
            MEDIAREMOTE_SERVICE: self._mrp_service,
            AIRPLAY_SERVICE: self._airplay_service
        }

        handler = supported_types.get(service_type)
        if handler:
            handler(service_name, address, port, properties)
        else:
            _LOGGER.warning('Discovered unknown device: %s', service_type)

    def _hs_service(self, service_name, address, port, properties):
        """Add a new device to discovered list."""
        identifier = service_name.split('.')[0]
        name = _property_decode(properties, 'Name')
        hsgid = _property_decode(properties, 'hG')
        service = conf.DmapService(identifier, hsgid, port=port)
        self._handle_service(address, name, service)

    def _non_hs_service(self, service_name, address, port, properties):
        """Add a new device without Home Sharing to discovered list."""
        identifier = service_name.split('.')[0]
        name = _property_decode(properties, 'CtlN')
        service = conf.DmapService(identifier, None, port=port)
        self._handle_service(address, name, service)

    def _mrp_service(self, _, address, port, properties):
        """Add a new MediaRemoteProtocol device to discovered list."""
        identifier = _property_decode(properties, 'UniqueIdentifier')
        name = _property_decode(properties, 'Name')
        service = conf.MrpService(identifier, port)
        self._handle_service(address, name, service)

    def _airplay_service(self, service_name, address, port, properties):
        """Add a new AirPlay device to discovered list."""
        identifier = _property_decode(properties, 'deviceid')
        name = service_name.replace('.' + AIRPLAY_SERVICE, '')
        service = conf.AirPlayService(identifier, port)
        self._handle_service(address, name, service)

    def _handle_service(self, address, name, service):
        if address not in self._found_devices:
            self._found_devices[address] = conf.AppleTV(address, name)

        _LOGGER.debug('Auto-discovered %s at %s:%d (%s)',
                      name, address, service.port, service.protocol)

        atv = self._found_devices[address]
        atv.add_service(service)


class ZeroconfScanner(BaseScanner):
    """Service discovery based on Zeroconf."""

    def __init__(self, loop):
        """Initialize a new ZeroconfScanner."""
        super().__init__()
        self.loop = loop

    async def discover(self, timeout):
        """Start discovery of devices and services."""
        zeroconf = Zeroconf(self.loop, address_family=[netifaces.AF_INET])
        try:
            ServiceBrowser(zeroconf, HOMESHARING_SERVICE, self)
            ServiceBrowser(zeroconf, DEVICE_SERVICE, self)
            ServiceBrowser(zeroconf, MEDIAREMOTE_SERVICE, self)
            ServiceBrowser(zeroconf, AIRPLAY_SERVICE, self)
            _LOGGER.debug('Discovering devices for %d seconds', timeout)
            await asyncio.sleep(timeout)
        finally:
            await zeroconf.close()
        return self._found_devices

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
        self.service_discovered(
            info.type, info.name, address, info.port, info.properties)


class UnicastMdnsScanner(BaseScanner):
    """Service discovery based on unicast MDNS."""

    def __init__(self, hosts, loop):
        """Initialize a new UnicastMdnsScanner."""
        super().__init__()
        self.hosts = hosts
        self.loop = loop

    async def discover(self, timeout):
        """Start discovery of devices and services."""
        results = await asyncio.gather(
            *[self._get_services(host, timeout) for host in self.hosts])
        for host, response in results:
            if response is not None:
                self._handle_response(host, response)
        return self._found_devices

    async def _get_services(self, host, timeout):
        port = os.environ.get('PYATV_UDNS_PORT', 5353)  # For testing purposes
        services = [s[0:-1] for s in ALL_SERVICES]
        try:
            response = await udns.request(
                self.loop, host, services, port=port, timeout=timeout)
        except asyncio.TimeoutError:
            response = None
        return host, response

    def _handle_response(self, host, response):
        for resource in response.resources:
            if resource.qtype != udns.QTYPE_TXT:
                continue

            service_name = '.'.join(resource.qname.split('.')[1:]) + '.'
            if service_name not in ALL_SERVICES:
                continue

            port = UnicastMdnsScanner._get_port(response, resource.qname)
            if not port:
                _LOGGER.warning('Missing port for %s', resource.qname)
                continue

            self.service_discovered(
                service_name, resource.qname + '.', host, port, resource.rd)

    @staticmethod
    def _get_port(response, qname):
        for resource in response.resources:
            if resource.qtype != udns.QTYPE_SRV:
                continue

            if resource.qname == qname:
                return resource.rd.get('port')

        return None


async def scan(loop, timeout=5, identifier=None, protocol=None, hosts=None):
    """Scan for Apple TVs using zeroconf (bonjour) and returns them."""
    def _should_include(atv):
        if identifier and identifier not in atv.all_identifiers:
            return False

        if protocol and atv.get_service(protocol) is None:
            return False

        return True

    if hosts:
        scanner = UnicastMdnsScanner(hosts, loop)
    else:
        scanner = ZeroconfScanner(loop)

    devices = (await scanner.discover(timeout)).values()
    return [device for device in devices if _should_include(device)]


async def connect(config, loop, protocol=None, session=None):
    """Connect and logins to an Apple TV."""
    if config.identifier is None:
        raise exceptions.DeviceIdMissingError("no device identifier")

    service = config.main_service(protocol=protocol)

    supported_implementations = {
        Protocol.DMAP: DmapAppleTV,
        Protocol.MRP: MrpAppleTV,
    }

    implementation = supported_implementations.get(service.protocol, None)
    if not implementation:
        raise exceptions.UnsupportedProtocolError(str(service.protocol))

    # If no session is given, create a default one
    if session is None:
        session = await net.create_session(loop=loop)

    # AirPlay stream API is the same for both DMAP and MRP
    airplay = AirPlayStreamAPI(config, loop)

    atv = implementation(loop, session, config, airplay)
    await atv.connect()
    return atv


async def pair(config, protocol, loop, session=None, **kwargs):
    """Pair with an Apple TV."""
    service = config.get_service(protocol)
    if not service:
        raise exceptions.NoServiceError(
            'no service available for protocol ' + str(protocol))

    protocol_handlers = {
        Protocol.DMAP: DmapPairingHandler,
        Protocol.MRP: MrpPairingHandler,
        Protocol.AirPlay: AirPlayPairingHandler,
    }

    handler = protocol_handlers.get(protocol, None)
    if handler is None:
        raise exceptions.UnsupportedProtocolError(str(protocol))

    if session is None:
        session = await net.create_session(loop)

    return handler(config, session, loop, **kwargs)
