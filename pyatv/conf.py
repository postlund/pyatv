"""Configuration when connecting to an Apple TV."""
from pyatv import (convert, exceptions)
from pyatv.const import Protocol, OperatingSystem
from pyatv.device_info import lookup_model, lookup_version
from pyatv.interface import DeviceInfo


class AppleTV:
    """Representation of an Apple TV configuration.

    An instance of this class represents a single device. A device can have
    several services, depending on the protocols it supports, e.g. DMAP or
    AirPlay.
    """

    def __init__(self, address, name):
        """Initialize a new AppleTV."""
        self.address = address
        self.name = name
        self._services = {}

    @property
    def identifier(self):
        """Return one of the identifiers associated with this device."""
        for prot in [Protocol.MRP, Protocol.DMAP, Protocol.AirPlay]:
            service = self.get_service(prot)
            if service:
                return service.identifier
        return None

    @property
    def all_identifiers(self):
        """Return all unique identifiers for this device."""
        services = self.services
        return [x.identifier for x in services if x.identifier is not None]

    def add_service(self, service):
        """Add a new service.

        If the service already exists, it will be merged.
        """
        existing = self._services.get(service.protocol)
        if existing is not None:
            existing.merge(service)
        else:
            self._services[service.protocol] = service

    def get_service(self, protocol):
        """Look up a service based on protocol.

        If a service with the specified protocol is not available, None is
        returned.
        """
        return self._services.get(protocol)

    @property
    def services(self):
        """Return all supported services."""
        services = set(self._services.keys())
        return [self.get_service(x) for x in services]

    def main_service(self, protocol=None):
        """Return suggested service used to establish connection."""
        protocols = [protocol] if protocol is not None else \
            [Protocol.MRP, Protocol.DMAP]

        for prot in protocols:
            service = self.get_service(prot)
            if service is not None:
                return service

        raise exceptions.NoServiceError(
            'no service to connect to')

    def set_credentials(self, protocol, credentials):
        """Set credentials for a protocol if it exists."""
        service = self.get_service(protocol)
        if service:
            service.credentials = credentials
            return True
        return False

    @property
    def device_info(self):
        """Return general device information."""
        properties = self._all_properties()

        if Protocol.MRP in self._services:
            os_type = OperatingSystem.TvOS
        elif Protocol.DMAP in self._services:
            os_type = OperatingSystem.Legacy
        else:
            os_type = OperatingSystem.Unknown

        build = properties.get('SystemBuildVersion')
        model = properties.get('model')
        version = properties.get('osvers', lookup_version(build))

        mac = properties.get(
            'macAddress', properties.get('deviceid'))
        if mac:
            mac = mac.upper()

        return DeviceInfo(os_type, version, build,
                          lookup_model(model), mac)

    def _all_properties(self):
        properties = {}
        for service in self.services:
            properties.update(service.properties)
        return properties

    def __eq__(self, other):
        """Compare instance with another instance."""
        if isinstance(other, self.__class__):
            return self.identifier == other.identifier
        return False

    def __str__(self):
        """Return a string representation of this object."""
        device_info = self.device_info
        services = [' - {0}'.format(s) for s in self._services.values()]
        identifiers = [' - {0}'.format(x) for x in self.all_identifiers]
        return '       Name: {0}\n' \
               '   Model/SW: {1}\n' \
               '    Address: {2}\n' \
               '        MAC: {3}\n' \
               'Identifiers:\n' \
               '{4}\n' \
               'Services:\n' \
               '{5}'.format(self.name, device_info, self.address,
                            device_info.mac,
                            '\n'.join(identifiers), '\n'.join(services))


# pylint: disable=too-few-public-methods
class BaseService:
    """Base class for protocol services."""

    def __init__(self, identifier, protocol, port, properties):
        """Initialize a new BaseService."""
        self.__identifier = identifier
        self.protocol = protocol
        self.port = port
        self.credentials = None
        self.properties = properties or {}

    @property
    def identifier(self):
        """Return unique identifier associated with this service."""
        return self.__identifier

    def merge(self, other):
        """Merge with other service of same type."""
        self.credentials = other.credentials or self.credentials
        self.properties.update(other.properties)

    def __str__(self):
        """Return a string representation of this object."""
        return 'Protocol: {0}, Port: {1}, Credentials: {2}'.format(
            convert.protocol_str(self.protocol), self.port,
            self.credentials)


# pylint: disable=too-few-public-methods
class DmapService(BaseService):
    """Representation of a DMAP service."""

    def __init__(self, identifier, credentials, port=None, properties=None):
        """Initialize a new DmapService."""
        super().__init__(identifier, Protocol.DMAP, port or 3689, properties)
        self.credentials = credentials


# pylint: disable=too-few-public-methods
class MrpService(BaseService):
    """Representation of a MediaRemote Protocol service."""

    def __init__(self, identifier, port, credentials=None, properties=None):
        """Initialize a new MrpService."""
        super().__init__(identifier, Protocol.MRP, port, properties)
        self.credentials = credentials


# pylint: disable=too-few-public-methods
class AirPlayService(BaseService):
    """Representation of an AirPlay service."""

    def __init__(self, identifier, port=7000,
                 credentials=None, properties=None):
        """Initialize a new AirPlayService."""
        super().__init__(identifier, Protocol.AirPlay, port, properties)
        self.credentials = credentials
