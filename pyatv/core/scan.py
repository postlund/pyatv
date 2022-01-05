"""Implementation of device scanning routines."""

from abc import ABC, abstractmethod
import asyncio
import contextlib
from ipaddress import IPv4Address, ip_address
import logging
import os
from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    Generator,
    Iterable,
    List,
    Mapping,
    NamedTuple,
    Optional,
    Set,
    Tuple,
    Union,
    cast,
)

from zeroconf import DNSPointer, DNSQuestionType
from zeroconf.asyncio import AsyncServiceInfo, AsyncZeroconf
from zeroconf.const import _CLASS_IN, _TYPE_PTR

from pyatv import conf
from pyatv.const import DeviceModel, Protocol
from pyatv.core import MutableService, mdns
from pyatv.helpers import (
    AIRPLAY_SERVICE,
    RAOP_SERVICE,
    get_unique_id,
    raop_name_from_service_name,
    sleep_proxy_name_from_service_name,
)
from pyatv.interface import BaseConfig, BaseService, DeviceInfo
from pyatv.support import knock
from pyatv.support.collections import CaseInsensitiveDict, dict_merge
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
DEVICE_INFO_TYPE: str = f"{DEVICE_INFO}."
SLEEP_PROXY: str = "_sleep-proxy._udp.local"
SLEEP_PROXY_TYPE: str = f"{SLEEP_PROXY}."
RAOP_TYPE: str = f"{RAOP_SERVICE}."
AIRPLAY_TYPE: str = f"{AIRPLAY_SERVICE}."
COMPANION_LINK_TYPE: str = "_companion-link._tcp.local."
NAME_USED_FOR_DEVICE_INFO = {
    COMPANION_LINK_TYPE,
    AIRPLAY_TYPE,
    RAOP_TYPE,
    SLEEP_PROXY_TYPE,
}

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


def _extract_service_name(info: AsyncServiceInfo) -> str:
    return info.name[: -(len(info.type) + 1)]


def _device_info_name(info: AsyncServiceInfo) -> Optional[str]:
    if info.type not in NAME_USED_FOR_DEVICE_INFO:
        return None
    short_name = _extract_service_name(info)
    if info.type == RAOP_TYPE:
        return raop_name_from_service_name(short_name)
    if info.type == SLEEP_PROXY_TYPE:
        return sleep_proxy_name_from_service_name(short_name)
    return short_name


def _first_non_link_local_or_v6_address(addresses: List[bytes]) -> Optional[str]:
    """Return the first ipv6 or non-link local ipv4 address."""
    for address in addresses:
        ip_addr = ip_address(address)
        if not ip_addr.is_link_local or ip_addr.version == 6:
            return str(ip_addr)
    return None


class AsyncDeviceInfoServiceInfo(AsyncServiceInfo):
    """A version of AsyncServiceInfo that does not expect addresses."""

    @property
    def _is_complete(self) -> bool:
        """Check if ServiceInfo has all expected properties.

        The _device-info._tcp.local. does not return an address
        so do not wait for it.
        """
        return self.text is not None


class ZeroconfScanner(BaseScanner):
    """Service discovery using zeroconf.

    A ServiceBrowser must be running for all the types we are browsing.
    """

    def __init__(
        self,
        aiozc: AsyncZeroconf,
        hosts: Optional[List[IPv4Address]] = None,
    ) -> None:
        """Initialize a new scanner."""
        super().__init__()
        self.aiozc = aiozc
        self.zeroconf = aiozc.zeroconf
        self.hosts: Set[str] = set(str(host) for host in hosts) if hosts else set()

    async def _async_services_by_addresses(
        self, zc_timeout: float
    ) -> Dict[str, List[AsyncServiceInfo]]:
        """Lookup services and aggregate them by address."""
        infos: List[AsyncServiceInfo] = []
        zc_types = {SLEEP_PROXY_TYPE, *(f"{service}." for service in self._services)}
        infos = [
            AsyncServiceInfo(zc_type, cast(DNSPointer, record).alias)
            for zc_type in zc_types
            for record in self.zeroconf.cache.async_all_by_details(
                zc_type, _TYPE_PTR, _CLASS_IN
            )
        ]
        await asyncio.gather(
            *[info.async_request(self.zeroconf, zc_timeout) for info in infos]
        )
        services_by_address: Dict[str, List[AsyncServiceInfo]] = {}
        for info in infos:
            address = _first_non_link_local_or_v6_address(info.addresses)
            if address:
                services_by_address.setdefault(address, []).append(info)
        return services_by_address

    async def _async_models_by_name(
        self, names: Iterable[str], zc_timeout: float
    ) -> Dict[str, str]:
        """Probe the DEVICE_INFO_TYPE."""
        _LOGGER.warning(
            "Probing _async_models_by_name: %s with timeout %s", names, zc_timeout
        )
        name_to_model: Dict[str, str] = {}
        device_infos = {
            name: AsyncDeviceInfoServiceInfo(
                DEVICE_INFO_TYPE, f"{name}.{DEVICE_INFO_TYPE}"
            )
            for name in names
        }
        await asyncio.gather(
            *[
                info.async_request(
                    self.zeroconf, zc_timeout, question_type=DNSQuestionType.QU
                )
                for info in device_infos.values()
            ]
        )
        for name, info in device_infos.items():
            possible_model = info.properties.get(b"model")
            if possible_model:
                with contextlib.suppress(UnicodeDecodeError):
                    name_to_model[name] = possible_model.decode("utf-8")
        return name_to_model

    def _async_process_responses(
        self,
        atv_services_by_address: Dict[str, List[mdns.Service]],
        name_to_model: Dict[str, str],
        name_by_address: Dict[str, str],
    ):
        """Process and callback each aggregated response to the base handler."""
        _LOGGER.warning(
            "Probing _async_process_responses: %s %s %s",
            atv_services_by_address,
            name_to_model,
            name_by_address,
        )
        for address, atv_services in atv_services_by_address.items():
            model = None
            name_for_address = name_by_address.get(address)
            if name_for_address is not None:
                possible_model = name_to_model.get(name_for_address)
                if possible_model:
                    model = possible_model
            self.handle_response(
                mdns.Response(
                    services=atv_services,
                    deep_sleep=all(
                        service.port == 0 and service.type != SLEEP_PROXY_TYPE
                        for service in atv_services
                    ),
                    model=model,
                )
            )

    async def process(self, timeout: int) -> None:
        """Start to process devices and services."""
        zc_timeout = timeout * 1000
        services_by_address = await self._async_services_by_addresses(zc_timeout)
        atv_services_by_address: Dict[str, List[mdns.Service]] = {}
        name_by_address: Dict[str, str] = {}
        for address, services in services_by_address.items():
            if self.hosts and address not in self.hosts:
                continue
            atv_services = []
            for service in services:
                atv_type = service.type[:-1]
                if address not in name_by_address:
                    device_info_name = _device_info_name(service)
                    if device_info_name:
                        name_by_address[address] = device_info_name
                atv_services.append(
                    mdns.Service(
                        atv_type,
                        _extract_service_name(service),
                        IPv4Address(address),
                        service.port,
                        CaseInsensitiveDict(
                            {
                                k.decode("ascii"): mdns.decode_value(v)
                                for k, v in service.properties.items()
                            }
                        ),
                    )
                )
            atv_services_by_address[address] = atv_services
        if not atv_services_by_address:
            return
        name_to_model = await self._async_models_by_name(
            name_by_address.values(), zc_timeout
        )
        self._async_process_responses(
            atv_services_by_address, name_to_model, name_by_address
        )
