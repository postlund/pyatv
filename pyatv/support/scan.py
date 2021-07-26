"""Implementation of device scanning routines."""

from abc import ABC, abstractmethod
import asyncio
from ipaddress import IPv4Address
import logging
import os
from typing import Callable, Dict, Generator, List, Mapping, NamedTuple, Optional, Tuple

from pyatv import conf, interface
from pyatv.const import DeviceModel
from pyatv.helpers import get_unique_id
from pyatv.support import knock, mdns
from pyatv.support.device_info import lookup_internal_name

_LOGGER = logging.getLogger(__name__)

ScanHandlerReturn = Tuple[str, interface.BaseService]
ScanHandler = Callable[[mdns.Service, mdns.Response], Optional[ScanHandlerReturn]]
ScanMethod = Callable[[], Mapping[str, ScanHandler]]

DEVICE_INFO: str = "_device-info._tcp.local"
SLEEP_PROXY: str = "_sleep-proxy._udp.local"

# These ports have been "arbitrarily" chosen (see issue #580) because a device normally
# listen on them (more or less). They are used as best-effort when for unicast scanning
# to try to wake up a device. Both issue #580 and #595 are good references to read.
KNOCK_PORTS: List[int] = [3689, 7000, 49152, 32498]


class FoundDevice(NamedTuple):
    """Represent a device found during scanning."""

    name: str
    address: IPv4Address
    deep_sleep: bool
    model: DeviceModel
    services: List[interface.BaseService]
    service_properties: Dict[str, Dict[str, str]]


def get_unique_identifiers(
    response: mdns.Response,
) -> Generator[Optional[str], None, None]:
    """Return (yield) all unique identifiers for a response."""
    for service in response.services:
        unique_id = get_unique_id(service.type, service.name, service.properties)
        if unique_id:
            yield unique_id


class BaseScanner(ABC):
    """Base scanner for service discovery."""

    def __init__(self) -> None:
        """Initialize a new BaseScanner."""
        self._services: Dict[str, ScanHandler] = {
            DEVICE_INFO: self._empty_handler,
            SLEEP_PROXY: self._empty_handler,
        }
        self._found_devices: Dict[IPv4Address, FoundDevice] = {}
        self._properties: Dict[IPv4Address, Dict[str, Mapping[str, str]]] = {}

    @staticmethod
    def _empty_handler(service: mdns.Service, response: mdns.Response) -> None:
        pass

    def add_service(self, service_type: str, handler: ScanHandler):
        """Add service type to discover."""
        self._services[service_type] = handler

    @property
    def services(self) -> List[str]:
        """Return list of service types to scan for."""
        return list(self._services.keys())

    async def discover(self, timeout: int) -> Mapping[IPv4Address, conf.AppleTV]:
        """Start discovery of devices and services."""
        await self.process(timeout)

        devices = {}
        for address, found_device in self._found_devices.items():
            devices[address] = conf.AppleTV(
                address,
                found_device.name,
                deep_sleep=found_device.deep_sleep,
                model=found_device.model,
                properties=self._properties[address],
            )
            for service in found_device.services:
                devices[address].add_service(service)
        return devices

    @abstractmethod
    async def process(self, timeout: int) -> None:
        """Start to process devices and services."""

    def handle_response(self, response: mdns.Response):
        """Call when an MDNS response was received."""
        for service in response.services:
            if service.type not in self._services:
                _LOGGER.warning(
                    "Discovered unsupported service %s for device %s",
                    service.name,
                    service.type,
                )
                continue

            try:
                self._service_discovered(service, response)
            except Exception:
                _LOGGER.exception("Failed to parse service: %s", service)

    def _service_discovered(
        self, service: mdns.Service, response: mdns.Response
    ) -> None:
        if service.address is None or service.port == 0:
            return

        result = self._services[service.type](service, response)
        if result:
            name, base_service = result
            _LOGGER.debug(
                "Auto-discovered %s at %s:%d via %s (%s)",
                service.name,
                service.address,
                service.port,
                base_service.protocol,
                service.properties,
            )

            if service.address not in self._found_devices:
                self._found_devices[service.address] = FoundDevice(
                    name,
                    service.address,
                    response.deep_sleep,
                    lookup_internal_name(response.model),
                    [],
                    {},
                )
            self._found_devices[service.address].services.append(base_service)

        # Save properties for all services belonging to a device/address
        if service.address is not None:
            if service.address not in self._properties:
                self._properties[service.address] = {}
            self._properties[service.address][service.type] = service.properties


class UnicastMdnsScanner(BaseScanner):
    """Service discovery based on unicast MDNS."""

    def __init__(
        self, hosts: List[IPv4Address], loop: asyncio.AbstractEventLoop
    ) -> None:
        """Initialize a new UnicastMdnsScanner."""
        super().__init__()
        self.hosts = hosts
        self.loop = loop

    async def process(self, timeout: int) -> None:
        """Start to process devices and services."""
        responses = await asyncio.gather(
            *[self._get_services(host, timeout) for host in self.hosts]
        )

        for response in responses:
            self.handle_response(response)

    async def _get_services(self, host: IPv4Address, timeout: int) -> mdns.Response:
        port = int(os.environ.get("PYATV_UDNS_PORT", 5353))  # For testing purposes
        knocker = None
        try:
            knocker = await knock.knocker(host, KNOCK_PORTS, self.loop, timeout=timeout)
            response = await mdns.unicast(
                self.loop,
                str(host),
                self.services,
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

    async def process(self, timeout: int) -> None:
        """Start to process devices and services."""
        responses = await mdns.multicast(
            self.loop,
            self.services,
            timeout=timeout,
            end_condition=self._end_if_identifier_found if self.identifier else None,
        )
        for response in responses:
            self.handle_response(response)

    def _end_if_identifier_found(self, response: mdns.Response):
        return self.identifier in get_unique_identifiers(response)
