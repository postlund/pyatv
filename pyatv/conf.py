"""Configuration used when connecting to a device.

A configuration describes a device, e.g. it's name, IP address and credentials. It is
possible to manually create a configuration, but generally scanning for devices will
provide configurations for you.
"""
from ipaddress import IPv4Address
from typing import Dict, List, Mapping, Optional

from pyatv.const import Protocol
from pyatv.interface import BaseConfig, BaseService, DeviceInfo


class AppleTV(BaseConfig):
    """Representation of a device configuration.

    An instance of this class represents a single device. A device can have
    several services depending on the protocols it supports, e.g. DMAP or
    AirPlay.
    """

    def __init__(
        self,
        address: IPv4Address,
        name: str,
        deep_sleep: bool = False,
        properties: Optional[Mapping[str, Mapping[str, str]]] = None,
        device_info: Optional[DeviceInfo] = None,
    ) -> None:
        """Initialize a new AppleTV."""
        super().__init__(properties or {})
        self._address = address
        self._name = name
        self._deep_sleep = deep_sleep
        self._services: Dict[Protocol, BaseService] = {}
        self._device_info = device_info or DeviceInfo({})

    @property
    def address(self) -> IPv4Address:
        """IP address of device."""
        return self._address

    @property
    def name(self) -> str:
        """Name of device."""
        return self._name

    @property
    def deep_sleep(self) -> bool:
        """If device is in deep sleep."""
        return self._deep_sleep

    def add_service(self, service: BaseService) -> None:
        """Add a new service.

        If the service already exists, it will be merged.
        """
        existing = self._services.get(service.protocol)
        if existing is not None:
            existing.merge(service)
        else:
            self._services[service.protocol] = service

    def get_service(self, protocol: Protocol) -> Optional[BaseService]:
        """Look up a service based on protocol.

        If a service with the specified protocol is not available, None is
        returned.
        """
        return self._services.get(protocol)

    @property
    def services(self) -> List[BaseService]:
        """Return all supported services."""
        return list(self._services.values())

    @property
    def device_info(self) -> DeviceInfo:
        """Return general device information."""
        return self._device_info


# pylint: disable=too-few-public-methods
class DmapService(BaseService):
    """Representation of a DMAP service."""

    def __init__(
        self,
        identifier: Optional[str],
        credentials: Optional[str],
        port: int = 3689,
        properties: Optional[Mapping[str, str]] = None,
    ) -> None:
        """Initialize a new DmapService."""
        super().__init__(identifier, Protocol.DMAP, port, properties, credentials)


# pylint: disable=too-few-public-methods
class MrpService(BaseService):
    """Representation of a MediaRemote Protocol (MRP) service."""

    def __init__(
        self,
        identifier: Optional[str],
        port: int,
        credentials: Optional[str] = None,
        properties: Optional[Mapping[str, str]] = None,
    ) -> None:
        """Initialize a new MrpService."""
        super().__init__(identifier, Protocol.MRP, port, properties, credentials)


# pylint: disable=too-few-public-methods
class AirPlayService(BaseService):
    """Representation of an AirPlay service."""

    def __init__(
        self,
        identifier: Optional[str],
        port: int = 7000,
        credentials: Optional[str] = None,
        properties: Optional[Mapping[str, str]] = None,
    ) -> None:
        """Initialize a new AirPlayService."""
        super().__init__(identifier, Protocol.AirPlay, port, properties, credentials)


# pylint: disable=too-few-public-methods
class CompanionService(BaseService):
    """Representation of a Companion link service."""

    def __init__(
        self,
        port: int,
        credentials: Optional[str] = None,
        properties: Optional[Mapping[str, str]] = None,
    ) -> None:
        """Initialize a new CompaniomService."""
        super().__init__(None, Protocol.Companion, port, properties, credentials)


# pylint: disable=too-few-public-methods
class RaopService(BaseService):
    """Representation of an RAOP service."""

    def __init__(
        self,
        identifier: Optional[str],
        port: int = 7000,
        credentials: Optional[str] = None,
        password: Optional[str] = None,
        properties: Optional[Mapping[str, str]] = None,
    ) -> None:
        """Initialize a new RaopService."""
        super().__init__(
            identifier, Protocol.RAOP, port, properties, credentials, password=password
        )
