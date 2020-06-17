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

HOMESHARING_SERVICE = "_appletv-v2._tcp.local."
DEVICE_SERVICE = "_touch-able._tcp.local."
MEDIAREMOTE_SERVICE = "_mediaremotetv._tcp.local."
AIRPLAY_SERVICE = "_airplay._tcp.local."

ALL_SERVICES = [
    HOMESHARING_SERVICE,
    DEVICE_SERVICE,
    MEDIAREMOTE_SERVICE,
    AIRPLAY_SERVICE,
]

# These ports have been "arbitrarily" chosen (see issue #580) because a device normally
# listen on them (more or less). They are used as best-effort when for unicast scanning
# to try to wake up a device. Both issue #580 and #595 are good references to read.
KNOCK_PORTS = [3689, 7000, 49152, 32498]


def _decode_properties(properties) -> Dict[str, str]:
    def _decode(value: bytes):
        try:
            # Remove non-breaking-spaces (0xA2A0, 0x00A0) before decoding
            return (
                value.replace(b"\xC2\xA0", b" ")
                .replace(b"\x00\xA0", b" ")
                .decode("utf-8")
            )
        except Exception:  # pylint: disable=broad-except
            return str(value)

    return {k.decode("utf-8"): _decode(v) for k, v in properties.items()}


class BaseScanner(ABC):  # pylint: disable=too-few-public-methods
    """Base scanner for service discovery."""

    def __init__(self) -> None:
        """Initialize a new BaseScanner."""
        self._found_devices = {}  # type: Dict[IPv4Address, conf.BaseService]

    @abstractmethod
    async def discover(self, timeout: int):
        """Start discovery of devices and services."""

    def service_discovered(  # pylint: disable=too-many-arguments
        self, service_type, service_name, address, port, properties
    ):
        """Call when a service was discovered."""
        supported_types = {
            HOMESHARING_SERVICE: self._hs_service,
            DEVICE_SERVICE: self._non_hs_service,
            MEDIAREMOTE_SERVICE: self._mrp_service,
            AIRPLAY_SERVICE: self._airplay_service,
        }

        handler = supported_types.get(service_type)
        if handler:
            handler(service_name, address, port, properties)
        else:
            _LOGGER.warning("Discovered unknown device: %s", service_type)

    def _hs_service(self, service_name, address, port, properties):
        """Add a new device to discovered list."""
        identifier = service_name.split(".")[0]
        name = properties.get("Name")
        hsgid = properties.get("hG")
        service = conf.DmapService(identifier, hsgid, port=port, properties=properties)
        self._handle_service(address, name, service)

    def _non_hs_service(self, service_name, address, port, properties):
        """Add a new device without Home Sharing to discovered list."""
        identifier = service_name.split(".")[0]
        name = properties.get("CtlN")
        service = conf.DmapService(identifier, None, port=port, properties=properties)
        self._handle_service(address, name, service)

    def _mrp_service(self, _, address, port, properties):
        """Add a new MediaRemoteProtocol device to discovered list."""
        identifier = properties.get("UniqueIdentifier")
        name = properties.get("Name")
        service = conf.MrpService(identifier, port, properties=properties)
        self._handle_service(address, name, service)

    def _airplay_service(self, service_name, address, port, properties):
        """Add a new AirPlay device to discovered list."""
        identifier = properties.get("deviceid")
        name = service_name.replace("." + AIRPLAY_SERVICE, "")
        service = conf.AirPlayService(identifier, port, properties=properties)
        self._handle_service(address, name, service)

    def _handle_service(self, address, name, service):
        if address not in self._found_devices:
            self._found_devices[address] = conf.AppleTV(address, name)

        _LOGGER.debug(
            "Auto-discovered %s at %s:%d (%s)",
            name,
            address,
            service.port,
            service.protocol,
        )

        atv = self._found_devices[address]
        atv.add_service(service)


class BaseMdnsScanner(BaseScanner):
    """Base scanner for MDNS service discovery."""

    def handle_response(self, host: IPv4Address, response: udns.DnsMessage):
        """Handle received DNS message."""
        for resource in response.answers + response.resources:
            if resource.qtype != udns.QTYPE_TXT:
                continue

            service_name = ".".join(resource.qname.split(".")[1:]) + "."
            if service_name not in ALL_SERVICES:
                continue

            port = BaseMdnsScanner._get_port(response, resource.qname)
            if not port:
                _LOGGER.warning("Missing port for %s", resource.qname)
                continue

            self.service_discovered(
                service_name,
                resource.qname + ".",
                host,
                port,
                _decode_properties(resource.rd),
            )

    @staticmethod
    def _get_port(response, qname):
        for resource in response.answers + response.resources:
            if resource.qtype != udns.QTYPE_SRV:
                continue

            if resource.qname == qname:
                return resource.rd.get("port")

        return None


class UnicastMdnsScanner(BaseMdnsScanner):
    """Service discovery based on unicast MDNS."""

    def __init__(self, hosts: List[IPv4Address], loop: asyncio.AbstractEventLoop):
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
            if response is not None:
                self.handle_response(host, response)
        return self._found_devices

    async def _get_services(self, host: IPv4Address, timeout: int):
        port = int(os.environ.get("PYATV_UDNS_PORT", 5353))  # For testing purposes
        services = [s[0:-1] for s in ALL_SERVICES]
        knocker = None
        try:
            knocker = await knock.knocker(host, KNOCK_PORTS, self.loop, timeout=timeout)
            response = await udns.unicast(
                self.loop, str(host), services, port=port, timeout=timeout
            )
        except asyncio.TimeoutError:
            response = None
        finally:
            if knocker:
                knocker.cancel()
        return host, response


class MulticastMdnsScanner(BaseMdnsScanner):
    """Service discovery based on multicast MDNS."""

    def __init__(self, loop: asyncio.AbstractEventLoop):
        """Initialize a new MulticastMdnsScanner."""
        super().__init__()
        self.loop = loop

    async def discover(self, timeout: int):
        """Start discovery of devices and services."""
        services = [s[0:-1] for s in ALL_SERVICES]
        results = await udns.multicast(self.loop, services)

        for host, response in results:
            if response is not None:
                self.handle_response(host, response)
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
