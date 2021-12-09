"""Minimalistic DNS-SD implementation."""
import asyncio
from ipaddress import IPv4Address
import logging
import time
import typing

from zeroconf import DNSQuestionType, ServiceListener, Zeroconf
from zeroconf.asyncio import AsyncServiceBrowser, AsyncServiceInfo, AsyncZeroconf

from pyatv import exceptions
from pyatv.support.collections import CaseInsensitiveDict

_LOGGER = logging.getLogger(__name__)

# Number of services to include in each request
SERVICES_PER_MSG = 3

SLEEP_PROXY_SERVICE = "_sleep-proxy._udp.local"
DEVICE_INFO_SERVICE = "_device-info._tcp.local"
ROAP_SERVICE = "_raop._tcp.local"

# This module produces a lot of debug output, use a dedicated log level.
# Maybe move this to top-level support later?
TRAFFIC_LEVEL = logging.DEBUG - 5
setattr(logging, "TRAFFIC", TRAFFIC_LEVEL)
logging.addLevelName(TRAFFIC_LEVEL, "Traffic")


class Service(typing.NamedTuple):
    """Represent an MDNS service."""

    type: str
    name: str
    address: typing.Optional[IPv4Address]
    port: int
    properties: typing.Mapping[str, str]


class Response(typing.NamedTuple):
    """Represent response to an MDNS request."""

    services: typing.List[Service]
    deep_sleep: bool
    model: typing.Optional[str]  # Comes from _device-info._tcp.local


def _atv_service_to_zc_service(service: str) -> str:
    if service[-1] != ".":
        return f"{service}."
    return service


def _zc_service_to_atv_service(service: str) -> str:
    if service[-1] != ".":
        return service
    return service[:-1]


def _decode_properties(
    properties: typing.Mapping[str, bytes],
) -> CaseInsensitiveDict[str]:
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

    return CaseInsensitiveDict(
        {k.decode("utf-8"): _decode(v) for k, v in properties.items()}
    )


def _get_model(services: typing.List[Service]) -> typing.Optional[str]:
    for service in services:
        if service.type == DEVICE_INFO_SERVICE:
            return service.properties.get("model")
    return None


def _response_from_services(services: typing.List[Service]) -> Response:
    return Response(
        services=services,
        deep_sleep=all(service.port == 0 for service in services),
        model=_get_model(services),
    )


def _base_name(name: str, type_: str) -> str:
    base_name = name[: -len(type_) - 1]
    if type_ == f"{ROAP_SERVICE}.":
        if "@" in base_name:
            return base_name.split("@")[1]
    if type_ == f"{SLEEP_PROXY_SERVICE}.":
        if " " in base_name:
            return base_name.split(" ", 2)[1]
    return base_name


class ATVServiceListener(ServiceListener):
    """A RecordUpdateListener that does not implement update_records."""

    def __init__(
        self,
        services: typing.List[str],
        timeout: int = 4,
        address: typing.Optional[str] = None,
        end_condition: typing.Optional[typing.Callable[[Response], bool]] = None,
        question_type: typing.Optional[DNSQuestionType] = None,
    ) -> None:
        """Init the listener."""
        self._services = set(services)
        self._address = address
        self._timeout = timeout
        self._finish = time.monotonic() + timeout
        self._end_condition = end_condition
        self._end_condition_met = asyncio.Event()
        self._services_by_address: typing.Dict[str, typing.List[Service]] = {}
        self._responses_by_address: typing.Dict[str, Response] = {}
        self._probed_device_info: typing.Set[str] = set()
        self._question_type = question_type
        self._seen = set()

    @property
    def responses(self) -> typing.List[Response]:
        """Generate response object from services."""
        return list(self._responses_by_address.values())

    async def async_wait(self) -> None:
        try:
            await asyncio.wait_for(
                self._end_condition_met.wait(), timeout=self._timeout
            )
        except asyncio.TimeoutError:
            return False
        return True

    def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        asyncio.create_task(self._async_service_info(zc, type_, name))

    def remove_service(self, zeroconf: Zeroconf, type: str, name: str) -> None:
        pass

    def update_service(self, zeroconf: Zeroconf, type: str, name: str) -> None:
        pass

    async def _async_service_info(self, zc: Zeroconf, type_: str, name: str):
        base_name = _base_name(name, type_)
        service = await self._async_get_single_service_info(
            zc, type_, name, self._address
        )
        address = str(service.address)
        services = self._services_by_address.setdefault(str(service.address), [])
        services.append(service)

        if base_name not in self._probed_device_info:
            self._probed_device_info.add(base_name)
            device_info_service = await self._async_get_single_service_info(
                zc, type_, name, address
            )
            services.append(device_info_service)

        response = _response_from_services(services)
        self._responses_by_address[address] = response
        if self._end_condition and self._end_condition(response):
            self._end_condition_met.set()

    async def _async_get_single_service_info(
        self,
        zc: Zeroconf,
        type_: str,
        name: str,
        address: typing.Optional[str] = None,
    ):
        info = AsyncServiceInfo(type_, name)
        await info.async_request(
            zc,
            (self._finish - time.monotonic()) * 1000,
            question_type=self._question_type,
        )
        if not address:
            for addr in [IPv4Address(address) for address in info.addresses]:
                if not addr.is_link_local:
                    address = addr
                    break
        return Service(
            _zc_service_to_atv_service(type_),
            name[: -len(type_) - 1],
            address,
            info.port,
            _decode_properties(info.properties),
        )


async def unicast(
    aiozc: AsyncZeroconf,
    address: str,
    services: typing.List[str],
    port: int = 5353,
    timeout: int = 4,
    end_condition: typing.Optional[typing.Callable[[Response], bool]] = None,
) -> Response:
    """Send request for services to a host."""
    responses = await _find_with_zeroconf(
        aiozc,
        services,
        address,
        port,
        timeout,
        end_condition=end_condition,
        question_type=DNSQuestionType.QU,
    )
    if responses:
        return responses[0]
    return Response([], False, None)


async def multicast(  # pylint: disable=too-many-arguments
    aiozc: AsyncZeroconf,
    services: typing.List[str],
    address: typing.Optional[str] = None,
    port: typing.Optional[int] = None,
    timeout: int = 4,
    end_condition: typing.Optional[typing.Callable[[Response], bool]] = None,
) -> typing.List[Response]:
    return await _find_with_zeroconf(
        aiozc, services, address, port, timeout, end_condition
    )


async def _find_with_zeroconf(  # pylint: disable=too-many-arguments
    aiozc: AsyncZeroconf,
    services: typing.List[str],
    address: typing.Optional[str] = None,
    port: typing.Optional[int] = None,
    timeout: int = 4,
    end_condition: typing.Optional[typing.Callable[[Response], bool]] = None,
    question_type: typing.Optional[DNSQuestionType] = None,
) -> typing.List[Response]:
    """Send multicast request for services."""
    zc_services = [_atv_service_to_zc_service(service) for service in services]
    update_listener = ATVServiceListener(
        zc_services, timeout, address, end_condition, question_type
    )
    browser = AsyncServiceBrowser(
        aiozc.zeroconf,
        zc_services,
        listener=update_listener,
        addr=address,
        port=port,
        question_type=question_type,
    )
    await update_listener.async_wait()
    await browser.async_cancel()
    return update_listener.responses


async def publish(
    loop: asyncio.AbstractEventLoop,
    service: Service,
    zconf: typing.Union[AsyncZeroconf, Zeroconf],
):
    """Publish an MDNS service on the network."""
    if service.address is None:
        raise exceptions.InvalidConfigError(
            f"no address for {service.name}.{service.type}"
        )
    if isinstance(zconf, AsyncZeroconf):
        aiozc = zconf
    else:
        aiozc = AsyncZeroconf(zc=zconf)

    zsrv = AsyncServiceInfo(
        f"{service.type}.",
        f"{service.name}.{service.type}.",
        addresses=[service.address.packed],
        port=service.port,
        properties=dict(service.properties),
    )

    _LOGGER.debug("Publishing zeroconf service: %s", zsrv)
    await aiozc.async_register_service(zsrv)

    async def _unregister():
        _LOGGER.debug("Unregistering service %s", zsrv)
        await aiozc.async_unregister_service(zsrv)

    return _unregister
