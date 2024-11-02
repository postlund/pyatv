"""Implementation of device scanning routines."""

from abc import ABC, abstractmethod
import asyncio
import contextlib
from ipaddress import IPv4Address
import logging
import os
from typing import (
    TYPE_CHECKING,
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

from zeroconf import (
    DNSOutgoing,
    DNSPointer,
    DNSQuestion,
    IPVersion,
    current_time_millis,
)
from zeroconf.asyncio import AsyncServiceInfo, AsyncZeroconf
from zeroconf.const import _CLASS_IN, _FLAGS_QR_QUERY, _TYPE_PTR

from pyatv import conf
from pyatv.const import DeviceModel, Protocol
from pyatv.core import MutableService, mdns
from pyatv.helpers import get_unique_id
from pyatv.interface import BaseConfig, BaseService, DeviceInfo
from pyatv.support import knock
from pyatv.support.collections import CaseInsensitiveDict, dict_merge
from pyatv.support.device_info import lookup_internal_name

_LOGGER = logging.getLogger(__name__)

ScanHandlerReturn = Tuple[str, MutableService]
ScanHandler = Callable[[mdns.Service, mdns.Response], Optional[ScanHandlerReturn]]
DeviceInfoNameFromShortName = Callable[[str], Optional[str]]
ScanHandlerDeviceInfoName = Tuple[ScanHandler, DeviceInfoNameFromShortName]
ScanMethod = Callable[[], Mapping[str, ScanHandlerDeviceInfoName]]

DevInfoExtractor = Callable[[str, Mapping[str, Any]], Mapping[str, Any]]
ServiceInfoMethod = Callable[
    [MutableService, DeviceInfo, Mapping[Protocol, BaseService]], Awaitable[None]
]

DEVICE_INFO: str = "_device-info._tcp.local"
DEVICE_INFO_TYPE: str = f"{DEVICE_INFO}."
SLEEP_PROXY: str = "_sleep-proxy._udp.local"
SLEEP_PROXY_TYPE: str = f"{SLEEP_PROXY}."

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


def device_info_name_from_unique_short_name(service_name: str) -> str:
    """Return the service name for device info when it is unique."""
    return service_name


def _sleep_proxy_device_info_name_from_short_name(service_name: str) -> str:
    """Convert an sleep proxy service name to a name."""
    return service_name.split(" ", maxsplit=1)[1]


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
        self._device_info_name: Dict[str, Callable[[str], Optional[str]]] = {
            SLEEP_PROXY: _sleep_proxy_device_info_name_from_short_name
        }
        self._service_infos: Dict[Protocol, ServiceInfoMethod] = {}
        self._found_devices: Dict[IPv4Address, FoundDevice] = {}
        self._properties: Dict[IPv4Address, Dict[str, Mapping[str, str]]] = {}

    def add_service(
        self,
        service_type: str,
        handler_device_info_name: ScanHandlerDeviceInfoName,
        device_info_extractor: DevInfoExtractor,
    ) -> None:
        """Add service type to discover."""
        handler, device_info_name = handler_device_info_name
        self._device_info_name[service_type] = device_info_name
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
    return _name_without_type(info.name, info.type)


def _name_without_type(name: str, type_: str) -> str:
    return name[: -(len(type_) + 1)]


def _get_valid_ipv4_address_from_service_info(
    info: AsyncServiceInfo,
) -> List[IPv4Address]:
    """Return valid IPv4 addresses from service info.

    Older airport devices (e.g. Airport Express) can return
    link-local addresses in the service info after the valid
    addresses. This function will filter out those addresses.
    """
    addresses = info.ip_addresses_by_version(IPVersion.V4Only)
    if TYPE_CHECKING:
        ipv4_addresses = cast(List[IPv4Address], addresses)
    else:
        ipv4_addresses = addresses
    return [
        ip_address
        for ip_address in ipv4_addresses
        if not ip_address.is_link_local
        and not ip_address.is_loopback
        and not ip_address.is_unspecified
    ]


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
    ) -> None:
        """Initialize a new scanner."""
        super().__init__()
        self.aiozc = aiozc
        self.zeroconf = aiozc.zeroconf
        self.address_to_device_name: Dict[IPv4Address, str] = {}
        self.device_name_to_address: Dict[str, IPv4Address] = {}

    def _set_or_get_address_to_device_name(
        self, address: IPv4Address, info: AsyncServiceInfo
    ) -> Optional[str]:
        """Get and cache address to device name mapping."""
        address_to_device_name = self.address_to_device_name
        if cached_name := address_to_device_name.get(address):
            return cached_name

        name = _extract_service_name(info)
        service_type = info.type[:-1]

        if device_name := self._device_info_name[service_type](name):
            address_to_device_name[address] = device_name
            self.device_name_to_address[device_name] = address
            return device_name

        return None

    def _build_service_info_queries(
        self,
    ) -> List[Union[AsyncServiceInfo, AsyncDeviceInfoServiceInfo]]:
        """Build AsyncServiceInfo queries from the requested types."""
        infos: List[Union[AsyncServiceInfo, AsyncDeviceInfoServiceInfo]] = []
        device_names = set()
        cache = self.zeroconf.cache
        for type_ in (SLEEP_PROXY, *self._services):
            if type_ == DEVICE_INFO:
                continue
            zc_type = f"{type_}."
            for record in cache.async_all_by_details(zc_type, _TYPE_PTR, _CLASS_IN):
                ptr_name = cast(DNSPointer, record).alias
                service_info = AsyncServiceInfo(zc_type, ptr_name)
                infos.append(service_info)
                name = _name_without_type(ptr_name, zc_type)
                device_name = self._device_info_name[type_](name)
                if device_name is not None and device_name not in device_names:
                    device_names.add(device_name)
                    device_service_info = AsyncDeviceInfoServiceInfo(
                        DEVICE_INFO_TYPE, f"{device_name}.{DEVICE_INFO_TYPE}"
                    )
                    infos.append(device_service_info)
        return infos

    def _process_responses(
        self,
        dev_services_by_address: Dict[IPv4Address, List[mdns.Service]],
        model_by_address: Dict[IPv4Address, Optional[str]],
    ) -> None:
        """Process and callback each aggregated response to the base handler."""
        for address, dev_services in dev_services_by_address.items():
            self.handle_response(
                mdns.Response(
                    services=dev_services,
                    deep_sleep=all(
                        service.port == 0 and service.type != SLEEP_PROXY_TYPE
                        for service in dev_services
                    ),
                    model=model_by_address.get(address),
                )
            )

    @abstractmethod
    async def _lookup_services_and_models(
        self, zc_timeout: float
    ) -> Tuple[Dict[IPv4Address, List[AsyncServiceInfo]], Dict[str, str]]:
        """Lookup services and aggregate them by address."""

    async def process(self, timeout: int) -> None:
        """Start to process devices and services."""
        zc_timeout = timeout * 1000
        services_by_address, name_to_model = await self._lookup_services_and_models(
            zc_timeout
        )
        dev_services_by_address: Dict[IPv4Address, List[mdns.Service]] = {}
        model_by_address: Dict[IPv4Address, Optional[str]] = {}
        for address, service_infos in services_by_address.items():
            dev_services: List[mdns.Service] = []
            for service_info in service_infos:
                if address not in model_by_address:
                    if device_name := self._set_or_get_address_to_device_name(
                        address, service_info
                    ):
                        model_by_address[address] = name_to_model.get(device_name)
                dev_services.append(
                    mdns.Service(
                        service_info.type[:-1],
                        _extract_service_name(service_info),
                        address,
                        service_info.port,
                        CaseInsensitiveDict(
                            {
                                k.decode("ascii"): mdns.decode_value(v)
                                for k, v in service_info.properties.items()
                            }
                        ),
                    )
                )
            dev_services_by_address[address] = dev_services
        self._process_responses(dev_services_by_address, model_by_address)

    def _process_service_info_responses(
        self,
        infos: List[AsyncServiceInfo],
    ) -> Tuple[Dict[IPv4Address, List[AsyncServiceInfo]], Dict[str, str]]:
        name_to_model: Dict[str, str] = {}
        services_by_address: Dict[IPv4Address, List[AsyncServiceInfo]] = {}
        for info in infos:
            if info.type == DEVICE_INFO_TYPE:
                model = info.properties.get(b"model")
                if model:
                    name = _extract_service_name(info)
                    with contextlib.suppress(UnicodeDecodeError):
                        name_to_model[name] = model.decode("utf-8")
            else:
                for ip_address in _get_valid_ipv4_address_from_service_info(info):
                    services_by_address.setdefault(ip_address, []).append(info)
        return services_by_address, name_to_model


class ZeroconfMulticastScanner(ZeroconfScanner):
    """Service discovery using zeroconf.

    A ServiceBrowser must be running for all the types we are browsing.
    """

    async def _lookup_services_and_models(
        self, zc_timeout: float
    ) -> Tuple[Dict[IPv4Address, List[AsyncServiceInfo]], Dict[str, str]]:
        """Lookup services and aggregate them by address."""
        infos = self._build_service_info_queries()
        now = current_time_millis()
        zeroconf = self.zeroconf
        requests: List[Awaitable[bool]] = [
            info.async_request(zeroconf, zc_timeout)
            for info in infos
            if not info.load_from_cache(zeroconf, now)
        ]
        if requests:
            await asyncio.gather(*requests)
        return self._process_service_info_responses(infos)


class ZeroconfUnicastScanner(ZeroconfScanner):
    """Service discovery using zeroconf.

    A ServiceBrowser should be running for all the types we are browsing,
    but we will fallback to sending unicast PTR queries for missing types
    in the event the network is dropping multicast responses for some
    reason.
    """

    def __init__(
        self,
        aiozc: AsyncZeroconf,
        hosts: List[IPv4Address],
    ) -> None:
        """Initialize a new scanner."""
        super().__init__(aiozc)
        self.hosts: Set[IPv4Address] = set(hosts) if hosts else set()
        # Once info_by_address_type is filled in, we are done.
        self.infos_by_address_type: Dict[
            IPv4Address, Dict[str, Optional[AsyncServiceInfo]]
        ] = {host: {f"{type_}.": None for type_ in self._services} for host in hosts}

    def _send_ptr_queries(self, address: IPv4Address, needed_types: List[str]) -> None:
        """Send PTR queries."""
        out = DNSOutgoing(_FLAGS_QR_QUERY)
        # Note that the multicast flag here is True even though we are sending
        # unicast queries. We still are speaking mdns and will be happy to get
        # a multicast response back.
        for type_ in needed_types:
            question = DNSQuestion(type_, _TYPE_PTR, _CLASS_IN)
            question.unicast = True
            out.add_question(question)
        self.zeroconf.async_send(out, str(address))

    def _process_service_infos(self, infos: List[AsyncServiceInfo]) -> None:
        """Process service infos and update self.infos_by_address_type."""
        device_infos: List[AsyncServiceInfo] = []
        infos_by_address_type = self.infos_by_address_type

        for info in infos:
            if info.type == DEVICE_INFO_TYPE:
                device_infos.append(info)
                # Device info is special because it does not have an address
                continue
            for ip_address in _get_valid_ipv4_address_from_service_info(info):
                if infos_by_type := infos_by_address_type.get(ip_address):
                    infos_by_type[info.type] = info
                    self._set_or_get_address_to_device_name(ip_address, info)

        # Device info is special because it does not have an address
        device_name_to_address = self.device_name_to_address
        for info in device_infos:
            name = _extract_service_name(info)
            if address := device_name_to_address.get(name):
                infos_by_address_type[address][DEVICE_INFO_TYPE] = info

    def _all_services_discovered(self) -> bool:
        """Check if all services have been discovered."""
        for types in self.infos_by_address_type.values():
            for info in types.values():
                if info is None:
                    return False
        return True

    def _process_matching_service_infos(
        self,
    ) -> Tuple[Dict[IPv4Address, List[AsyncServiceInfo]], Dict[str, str]]:
        """Return all matching service infos for the requested hosts."""
        return self._process_service_info_responses(
            [
                info
                for types in self.infos_by_address_type.values()
                for info in types.values()
                if info is not None
            ]
        )

    async def _load_from_cache_or_send_queries(
        self, infos: List[AsyncServiceInfo], zc_timeout: float
    ) -> bool:
        """Load from cache or send queries."""
        zeroconf = self.zeroconf
        infos_to_send: List[AsyncServiceInfo] = []
        infos_with_cache: List[AsyncServiceInfo] = []
        now = current_time_millis()
        for info in infos:
            if info.load_from_cache(zeroconf, now):
                infos_with_cache.append(info)
            else:
                infos_to_send.append(info)

        self._process_service_infos(infos_with_cache)
        # If all services are cached, we are done
        if self._all_services_discovered():
            return True

        # If there are no infos that need to make requests, we are done
        if not infos_to_send:
            return False

        zeroconf = self.zeroconf
        host_strs = [str(host) for host in self.hosts]
        await asyncio.gather(
            *(
                info.async_request(zeroconf, zc_timeout, host_str)
                for host_str in host_strs
                for info in infos_to_send
            )
        )
        self._process_service_infos(infos_to_send)
        # If all services are filled we are done
        return self._all_services_discovered()

    async def _lookup_services_and_models(
        self, zc_timeout: float
    ) -> Tuple[Dict[IPv4Address, List[AsyncServiceInfo]], Dict[str, str]]:
        """Lookup services and aggregate them by address."""
        infos = self._build_service_info_queries()
        if await self._load_from_cache_or_send_queries(infos, zc_timeout):
            return self._process_matching_service_infos()

        # Multicast is likely broken, the device is offline,
        # or the network is dropping multicast responses.
        # We will try to send unicast PTR queries for the missing types.
        infos_by_address_type = self.infos_by_address_type
        for host in self.hosts:
            # We do not send queries for sleep proxy because
            # sleepy proxy is not useful if multicast is broken
            # and its not required to complete service discovery.
            if needed_types := [
                type_
                for type_, info in infos_by_address_type[host].items()
                if info is None and type_ != SLEEP_PROXY_TYPE
            ]:
                _LOGGER.debug(
                    "%s: Multicast is broken or device offline, "
                    "trying unicast PTR queries for %s",
                    host,
                    needed_types,
                )
                self._send_ptr_queries(host, needed_types)

        # Wait for the PTR queries to complete. We have no way
        # to know when they are done, so we just wait for the
        # timeout to expire.
        await asyncio.sleep(zc_timeout / 1000)
        # Now that we have sent the PTR queries we check the
        # cache again for any new info and refresh any incomplete
        # info that we have.
        infos = self._build_service_info_queries()
        await self._load_from_cache_or_send_queries(infos, zc_timeout)
        return self._process_matching_service_infos()
