"""Implementation of device scanning routines."""

from abc import ABC, abstractmethod
import asyncio
from ipaddress import IPv4Address
import logging
import os
from typing import Dict, Generator, List, Mapping, Optional

from pyatv import conf, interface
from pyatv.helpers import get_unique_id
from pyatv.support import knock, mdns
from pyatv.support.device_info import lookup_internal_name

_LOGGER = logging.getLogger(__name__)

HOMESHARING_SERVICE: str = "_appletv-v2._tcp.local"
DEVICE_SERVICE: str = "_touch-able._tcp.local"
MEDIAREMOTE_SERVICE: str = "_mediaremotetv._tcp.local"
AIRPLAY_SERVICE: str = "_airplay._tcp.local"
COMPANION_SERVICE: str = "_companion-link._tcp.local"
RAOP_SERVICE: str = "_raop._tcp.local"
AIRPORT_ADMIN_SERVICE: str = "_airport._tcp.local"

# These corresponds to services mapped to a protocol
ALL_SERVICES: List[str] = [
    HOMESHARING_SERVICE,
    DEVICE_SERVICE,
    MEDIAREMOTE_SERVICE,
    AIRPLAY_SERVICE,
    COMPANION_SERVICE,
    RAOP_SERVICE,
]

# Services that does not map to a protocol but provides additional metadata
EXTRA_SERVICES: List[str] = [AIRPORT_ADMIN_SERVICE]

# These ports have been "arbitrarily" chosen (see issue #580) because a device normally
# listen on them (more or less). They are used as best-effort when for unicast scanning
# to try to wake up a device. Both issue #580 and #595 are good references to read.
KNOCK_PORTS: List[int] = [3689, 7000, 49152, 32498]


def _get_service_properties(
    services: List[mdns.Service], service_type
) -> Mapping[str, str]:
    for service in services:
        if service.type == service_type:
            return service.properties
    return {}


def get_unique_identifiers(
    response: mdns.Response,
) -> Generator[Optional[str], None, None]:
    """Return (yield) all unique identifiers for a response."""
    for service in response.services:
        unique_id = get_unique_id(service.type, service.name, service.properties)
        if unique_id:
            yield unique_id


class BaseScanner(ABC):  # pylint: disable=too-few-public-methods
    """Base scanner for service discovery."""

    def __init__(self) -> None:
        """Initialize a new BaseScanner."""
        self._found_devices: Dict[IPv4Address, conf.AppleTV] = {}

    @abstractmethod
    async def discover(self, timeout: int):
        """Start discovery of devices and services."""

    def handle_response(self, response: mdns.Response):
        """Call when an MDNS response was received."""
        for service in response.services:
            if service.address and service.port != 0:
                try:
                    self._service_discovered(service, response)
                except Exception:
                    _LOGGER.warning("Failed to parse service: %s", service)

    def _service_discovered(
        self, service: mdns.Service, response: mdns.Response
    ) -> None:
        {
            HOMESHARING_SERVICE: self._hs_service,
            DEVICE_SERVICE: self._non_hs_service,
            MEDIAREMOTE_SERVICE: self._mrp_service,
            AIRPLAY_SERVICE: self._airplay_service,
            COMPANION_SERVICE: self._companion_service,
            RAOP_SERVICE: self._raop_service,
        }.get(service.type, self._unsupported_service)(service, response)

    def _hs_service(self, mdns_service: mdns.Service, response: mdns.Response) -> None:
        """Add a new device to discovered list."""
        name = mdns_service.properties.get("Name", "Unknown")
        service = conf.DmapService(
            get_unique_id(
                mdns_service.type, mdns_service.name, mdns_service.properties
            ),
            mdns_service.properties.get("hG"),
            port=mdns_service.port,
            properties=mdns_service.properties,
        )
        self._handle_service(mdns_service.address, name, service, response)

    def _non_hs_service(
        self, mdns_service: mdns.Service, response: mdns.Response
    ) -> None:
        """Add a new device without Home Sharing to discovered list."""
        name = mdns_service.properties.get("CtlN", "Unknown")
        service = conf.DmapService(
            get_unique_id(
                mdns_service.type, mdns_service.name, mdns_service.properties
            ),
            None,
            port=mdns_service.port,
            properties=mdns_service.properties,
        )
        self._handle_service(mdns_service.address, name, service, response)

    def _mrp_service(self, mdns_service: mdns.Service, response: mdns.Response) -> None:
        """Add a new MediaRemoteProtocol device to discovered list."""
        name = mdns_service.properties.get("Name", "Unknown")
        service = conf.MrpService(
            get_unique_id(
                mdns_service.type, mdns_service.name, mdns_service.properties
            ),
            mdns_service.port,
            properties=mdns_service.properties,
        )
        self._handle_service(mdns_service.address, name, service, response)

    def _airplay_service(
        self, mdns_service: mdns.Service, response: mdns.Response
    ) -> None:
        """Add a new AirPlay device to discovered list."""
        service = conf.AirPlayService(
            get_unique_id(
                mdns_service.type, mdns_service.name, mdns_service.properties
            ),
            mdns_service.port,
            properties=mdns_service.properties,
        )
        self._handle_service(mdns_service.address, mdns_service.name, service, response)

    def _companion_service(self, mdns_service: mdns.Service, response: mdns.Response):
        """Add a new companion device to discovered list."""
        service = conf.CompanionService(
            mdns_service.port,
            properties=mdns_service.properties,
        )
        self._handle_service(mdns_service.address, mdns_service.name, service, response)

    def _raop_service(self, mdns_service: mdns.Service, response: mdns.Response):
        """Add a new RAOP device to discovered list."""
        _, name = mdns_service.name.split("@", maxsplit=1)
        service = conf.RaopService(
            get_unique_id(
                mdns_service.type, mdns_service.name, mdns_service.properties
            ),
            mdns_service.port,
            properties=mdns_service.properties,
        )
        self._handle_service(mdns_service.address, name, service, response)

    @staticmethod
    def _unsupported_service(mdns_service: mdns.Service, _: mdns.Response) -> None:
        """Handle unsupported service."""
        if mdns_service.type not in EXTRA_SERVICES:
            _LOGGER.warning(
                "Discovered unknown device %s (%s)",
                mdns_service.name,
                mdns_service.type,
            )

    def _handle_service(
        self,
        address,
        name: str,
        service: interface.BaseService,
        response: mdns.Response,
    ) -> None:
        _LOGGER.debug(
            "Auto-discovered %s at %s:%d (%s)",
            name,
            address,
            service.port,
            service.protocol,
        )

        if address not in self._found_devices:
            # Extract properties from extra services that might be of interest
            extra_properties: Dict[str, str] = {}
            for extra_service in EXTRA_SERVICES:
                extra_properties.update(
                    _get_service_properties(response.services, extra_service)
                )

            self._found_devices[address] = conf.AppleTV(
                address,
                name,
                deep_sleep=response.deep_sleep,
                model=lookup_internal_name(response.model),
                properties=extra_properties,
            )

        self._found_devices[address].add_service(service)


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
        responses = await asyncio.gather(
            *[self._get_services(host, timeout) for host in self.hosts]
        )

        for response in responses:
            self.handle_response(response)
        return self._found_devices

    async def _get_services(self, host: IPv4Address, timeout: int) -> mdns.Response:
        port = int(os.environ.get("PYATV_UDNS_PORT", 5353))  # For testing purposes
        knocker = None
        try:
            knocker = await knock.knocker(host, KNOCK_PORTS, self.loop, timeout=timeout)
            response = await mdns.unicast(
                self.loop,
                str(host),
                ALL_SERVICES + EXTRA_SERVICES,
                port=port,
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            return mdns.Response([], False, None)
        finally:
            if knocker:
                knocker.cancel()
        return response


class MulticastMdnsScanner(BaseScanner):
    """Service discovery based on multicast MDNS."""

    def __init__(
        self, loop: asyncio.AbstractEventLoop, identifier: Optional[str] = None
    ):
        """Initialize a new MulticastMdnsScanner."""
        super().__init__()
        self.loop = loop
        self.identifier = identifier

    async def discover(self, timeout: int):
        """Start discovery of devices and services."""
        responses = await mdns.multicast(
            self.loop,
            ALL_SERVICES + EXTRA_SERVICES,
            timeout=timeout,
            end_condition=self._end_if_identifier_found if self.identifier else None,
        )
        for _, response in responses.items():
            self.handle_response(response)
        return self._found_devices

    def _end_if_identifier_found(self, response: mdns.Response):
        return self.identifier in get_unique_identifiers(response)
