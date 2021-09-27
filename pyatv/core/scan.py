"""Implementation of device scanning routines."""

from abc import ABC, abstractmethod
import asyncio
from ipaddress import IPv4Address
import logging
import os
from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    Generator,
    List,
    Mapping,
    NamedTuple,
    Optional,
    Set,
    Tuple,
    Union,
    cast,
)

from pyatv import conf
from pyatv.const import DeviceModel, Protocol
from pyatv.core import MutableService, mdns
from pyatv.helpers import get_unique_id
from pyatv.interface import BaseConfig, BaseService, DeviceInfo
from pyatv.support import knock
from pyatv.support.collections import dict_merge
from pyatv.support.device_info import lookup_internal_name

_LOGGER = logging.getLogger(__name__)

ScanHandlerReturn = Tuple[str, MutableService]
ScanHandler = Callable[[mdns.Service, mdns.Response], Optional[ScanHandlerReturn]]
ScanMethod = Callable[[], Mapping[str, ScanHandler]]

DevInfoExtractor = Callable[[str, Mapping[str, Any]], Mapping[str, Any]]
ServiceInfoMethod = Callable[
    [MutableService, DeviceInfo, Mapping[Protocol, BaseService]], Awaitable[None]
]

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
    services: List[MutableService]


def get_unique_identifiers(
    response: mdns.Response,
) -> Generator[Optional[str], None, None]:
    """Return (yield) all unique identifiers for a response."""
    for service in response.services:
        unique_id = get_unique_id(service.type, service.name, service.properties)
        if unique_id:
            yield unique_id


def _empty_handler(service: mdns.Service, response: mdns.Response) -> None:
    pass


def _empty_extractor(
    service_type: str, properties: Mapping[str, Any]
) -> Mapping[str, Any]:
    return {}


class BaseScanner(ABC):
    """Base scanner for service discovery."""

    def __init__(self) -> None:
        """Initialize a new BaseScanner."""
        self._services: Dict[str, Tuple[ScanHandler, DevInfoExtractor]] = {
            DEVICE_INFO: (_empty_handler, _empty_extractor),
            SLEEP_PROXY: (_empty_handler, _empty_extractor),
        }
        self._service_infos: Dict[Protocol, ServiceInfoMethod] = {}
        self._found_devices: Dict[IPv4Address, FoundDevice] = {}
        self._properties: Dict[IPv4Address, Dict[str, Mapping[str, str]]] = {}

    def add_service(
        self,
        service_type: str,
        handler: ScanHandler,
        device_info_extractor: DevInfoExtractor,
    ) -> None:
        """Add service type to discover."""
        self._services[service_type] = (handler, device_info_extractor)

    def add_service_info(
        self, protocol: Protocol, service_info: ServiceInfoMethod
    ) -> None:
        """Add service info updater method."""
        self._service_infos[protocol] = service_info

    @property
    def services(self) -> List[str]:
        """Return list of service types to scan for."""
        return list(self._services.keys())

    async def discover(self, timeout: int) -> Mapping[IPv4Address, BaseConfig]:
        """Start discovery of devices and services."""
        await self.process(timeout)

        devices = {}
        for address, found_device in self._found_devices.items():
            device_info = self._get_device_info(found_device)

            devices[address] = conf.AppleTV(
                address,
                found_device.name,
                deep_sleep=found_device.deep_sleep,
                properties=self._properties[address],
                device_info=device_info,
            )

            for service in found_device.services:
                devices[address].add_service(service)

            properties_map = {
                service.protocol: service for service in devices[address].services
            }

            for device_service in devices[address].services:
                # Apply service_info after adding all services in case a merge happens.
                # We know services are of type MutableService here.
                await self._service_infos[device_service.protocol](
                    cast(MutableService, device_service), device_info, properties_map
                )

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

        result = self._services[service.type][0](service, response)
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
                )
            self._found_devices[service.address].services.append(base_service)

        # Save properties for all services belonging to a device/address
        if service.address is not None:
            if service.address not in self._properties:
                self._properties[service.address] = {}
            self._properties[service.address][service.type] = service.properties

    def _get_device_info(self, device: FoundDevice) -> DeviceInfo:
        device_info: Dict[str, Any] = {}

        # Extract device info from all service responses
        device_properties = self._properties[device.address]
        for service_name, service_properties in device_properties.items():
            service_info = self._services.get(service_name)
            if service_info:
                _, extractor = service_info
                dict_merge(device_info, extractor(service_name, service_properties))

        # If model was discovered via _device-info._tcp.local, manually add that
        # to the device info
        if device.model != DeviceModel.Unknown:
            dict_merge(device_info, {DeviceInfo.MODEL: device.model})

        return DeviceInfo(device_info)


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
        self,
        loop: asyncio.AbstractEventLoop,
        identifier: Optional[Union[str, Set[str]]] = None,
    ):
        """Initialize a new MulticastMdnsScanner."""
        super().__init__()
        self.loop = loop
        self.identifier: Optional[Set[str]] = (
            {identifier} if isinstance(identifier, str) else identifier
        )

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
        return self.identifier and not self.identifier.isdisjoint(
            set(get_unique_identifiers(response))
        )
