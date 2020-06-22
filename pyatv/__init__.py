"""Main routines for interacting with an Apple TV."""

import os
import asyncio
import logging
import datetime  # noqa
from abc import ABC, abstractmethod
from ipaddress import IPv4Address
from typing import List, Dict

import aiohttp

from pyatv import conf, exceptions, interface
from pyatv.airplay import AirPlayStreamAPI
from pyatv.const import Protocol
from pyatv.dmap import DmapAppleTV
from pyatv.dmap.pairing import DmapPairingHandler
from pyatv.mrp import MrpAppleTV
from pyatv.mrp.pairing import MrpPairingHandler
from pyatv.airplay.pairing import AirPlayPairingHandler
from pyatv.support import net, knock, udns


_LOGGER = logging.getLogger(__name__)

HOMESHARING_SERVICE: str = "_appletv-v2._tcp.local"
DEVICE_SERVICE: str = "_touch-able._tcp.local"
MEDIAREMOTE_SERVICE: str = "_mediaremotetv._tcp.local"
AIRPLAY_SERVICE: str = "_airplay._tcp.local"

ALL_SERVICES: List[str] = [
    HOMESHARING_SERVICE,
    DEVICE_SERVICE,
    MEDIAREMOTE_SERVICE,
    AIRPLAY_SERVICE,
]

# These ports have been "arbitrarily" chosen (see issue #580) because a device normally
# listen on them (more or less). They are used as best-effort when for unicast scanning
# to try to wake up a device. Both issue #580 and #595 are good references to read.
KNOCK_PORTS: List[int] = [3689, 7000, 49152, 32498]


class BaseScanner(ABC):  # pylint: disable=too-few-public-methods
    """Base scanner for service discovery."""

    def __init__(self) -> None:
        """Initialize a new BaseScanner."""
        self._found_devices: Dict[IPv4Address, conf.AppleTV] = {}

    @abstractmethod
    async def discover(self, timeout: int):
        """Start discovery of devices and services."""

    def service_discovered(self, service: udns.Service) -> None:
        """Call when a service was discovered."""
        {
            HOMESHARING_SERVICE: self._hs_service,
            DEVICE_SERVICE: self._non_hs_service,
            MEDIAREMOTE_SERVICE: self._mrp_service,
            AIRPLAY_SERVICE: self._airplay_service,
        }.get(service.type, self._unsupported_service)(service)

    def _hs_service(self, mdns_service: udns.Service) -> None:
        """Add a new device to discovered list."""
        name = mdns_service.properties.get("Name")
        service = conf.DmapService(
            mdns_service.name,
            mdns_service.properties.get("hG"),
            port=mdns_service.port,
            properties=mdns_service.properties,
        )
        self._handle_service(mdns_service.address, name, service)

    def _non_hs_service(self, mdns_service: udns.Service) -> None:
        """Add a new device without Home Sharing to discovered list."""
        name = mdns_service.properties.get("CtlN")
        service = conf.DmapService(
            mdns_service.name,
            None,
            port=mdns_service.port,
            properties=mdns_service.properties,
        )
        self._handle_service(mdns_service.address, name, service)

    def _mrp_service(self, mdns_service: udns.Service) -> None:
        """Add a new MediaRemoteProtocol device to discovered list."""
        name = mdns_service.properties.get("Name")
        service = conf.MrpService(
            mdns_service.properties.get("UniqueIdentifier"),
            mdns_service.port,
            properties=mdns_service.properties,
        )
        self._handle_service(mdns_service.address, name, service)

    def _airplay_service(self, mdns_service: udns.Service) -> None:
        """Add a new AirPlay device to discovered list."""
        service = conf.AirPlayService(
            mdns_service.properties.get("deviceid"),
            mdns_service.port,
            properties=mdns_service.properties,
        )
        self._handle_service(mdns_service.address, mdns_service.name, service)

    def _unsupported_service(self, mdns_service: udns.Service) -> None:
        """Handle unsupported service."""
        _LOGGER.warning(
            "Discovered unknown device %s (%s)", mdns_service.name, mdns_service.type
        )

    def _handle_service(self, address, name, service) -> None:
        _LOGGER.debug(
            "Auto-discovered %s at %s:%d (%s)",
            name,
            address,
            service.port,
            service.protocol,
        )

        atv = self._found_devices.setdefault(address, conf.AppleTV(address, name))
        atv.add_service(service)


class UnicastMdnsScanner(BaseScanner):
    """Service discovery based on unicast MDNS."""

    def __init__(
        self, hosts: List[IPv4Address], loop: asyncio.AbstractEventLoop
    ) -> None:
        """Initialize a new UnicastMdnsScanner."""
        super().__init__()
        self.hosts = hosts
        self.loop = loop

    async def discover(self, timeout: int):
        """Start discovery of devices and services."""
        results = await asyncio.gather(
            *[self._get_services(host, timeout) for host in self.hosts]
        )

        for host, response in results:
            if response is None:
                continue

            for service in udns.parse_services(response):
                if service.address and service.port != 0:
                    self.service_discovered(service)

        return self._found_devices

    async def _get_services(self, host: IPv4Address, timeout: int):
        port = int(os.environ.get("PYATV_UDNS_PORT", 5353))  # For testing purposes
        knocker = None
        try:
            knocker = await knock.knocker(host, KNOCK_PORTS, self.loop, timeout=timeout)
            response = await udns.unicast(
                self.loop, str(host), ALL_SERVICES, port=port, timeout=timeout
            )
        except asyncio.TimeoutError:
            return host, None
        finally:
            if knocker:
                knocker.cancel()
        return host, response


class MulticastMdnsScanner(BaseScanner):
    """Service discovery based on multicast MDNS."""

    def __init__(self, loop: asyncio.AbstractEventLoop):
        """Initialize a new MulticastMdnsScanner."""
        super().__init__()
        self.loop = loop

    async def discover(self, timeout: int):
        """Start discovery of devices and services."""
        results = await udns.multicast(self.loop, ALL_SERVICES)

        for response in results.values():
            for service in udns.parse_services(response):
                if service.address and service.port != 0:
                    self.service_discovered(service)
        return self._found_devices


async def scan(
    loop: asyncio.AbstractEventLoop,
    timeout: int = 5,
    identifier: str = None,
    protocol: Protocol = None,
    hosts: List[str] = None,
) -> List[conf.AppleTV]:
    """Scan for Apple TVs on network and return their configurations."""

    def _should_include(atv):
        if not atv.ready:
            return False

        if identifier and identifier not in atv.all_identifiers:
            return False

        if protocol and atv.get_service(protocol) is None:
            return False

        return True

    scanner: BaseScanner
    if hosts:
        scanner = UnicastMdnsScanner([IPv4Address(host) for host in hosts], loop)
    else:
        scanner = MulticastMdnsScanner(loop)

    devices = (await scanner.discover(timeout)).values()
    return [device for device in devices if _should_include(device)]


async def connect(
    config: conf.AppleTV,
    loop: asyncio.AbstractEventLoop,
    protocol: Protocol = None,
    session: aiohttp.ClientSession = None,
) -> interface.AppleTV:
    """Connect to a device based on a configuration."""
    if config.identifier is None:
        raise exceptions.DeviceIdMissingError("no device identifier")

    service = config.main_service(protocol=protocol)

    implementation = {Protocol.DMAP: DmapAppleTV, Protocol.MRP: MrpAppleTV}.get(
        service.protocol
    )

    if not implementation:
        raise exceptions.UnsupportedProtocolError(str(service.protocol))

    # AirPlay stream API is the same for both DMAP and MRP
    airplay = AirPlayStreamAPI(config, loop)

    atv = implementation(loop, await net.create_session(session), config, airplay)
    await atv.connect()
    return atv


async def pair(
    config: conf.AppleTV,
    protocol: Protocol,
    loop: asyncio.AbstractEventLoop,
    session: aiohttp.ClientSession = None,
    **kwargs
):
    """Pair a protocol for an Apple TV."""
    service = config.get_service(protocol)
    if not service:
        raise exceptions.NoServiceError(
            "no service available for protocol " + str(protocol)
        )

    handler = {
        Protocol.DMAP: DmapPairingHandler,
        Protocol.MRP: MrpPairingHandler,
        Protocol.AirPlay: AirPlayPairingHandler,
    }.get(protocol)

    if handler is None:
        raise exceptions.UnsupportedProtocolError(str(protocol))

    return handler(config, await net.create_session(session), loop, **kwargs)
