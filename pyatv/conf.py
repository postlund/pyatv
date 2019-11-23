"""Configuration when connecting to an Apple TV."""
from pyatv import (convert, exceptions)
from pyatv.const import (PROTOCOL_MRP, PROTOCOL_DMAP, PROTOCOL_AIRPLAY)


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
        self._identifier = None

    @property
    def identifier(self):
        """Return one of the identifiers associated with this device."""
        return self._identifier

    @property
    def all_identifiers(self):
        """Return all unique identifiers for this device."""
        services = self.services
        return [x.identifier for x in services if x.identifier is not None]

    def add_service(self, service):
        """Add a new service.

        If the service already exists, it will be merged.
        """
        existing = self._services.get(service.protocol, None)
        if existing is not None:
            existing.merge(service)
        else:
            self._services[service.protocol] = service

        if self._identifier is None:
            self._identifier = service.identifier

    def get_service(self, protocol):
        """Look up a service based on protocol.

        If a service with the specified protocol is not available, None is
        returned.
        """
        # Special case for AirPlay for now
        if protocol == PROTOCOL_AIRPLAY:
            if self._services.get(protocol, None) is None:
                self._services[protocol] = AirPlayService(None, 7000)

        return self._services.get(protocol, None)

    @property
    def services(self):
        """Return all supported services."""
        services = set(list(self._services.keys()) + [PROTOCOL_AIRPLAY])
        return [self.get_service(x) for x in services]

    def main_service(self, protocol=None):
        """Return suggested service used to establish connection."""
        protocols = [protocol] if protocol is not None else \
            [PROTOCOL_MRP, PROTOCOL_DMAP]

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

    def __eq__(self, other):
        """Compare instance with another instance."""
        if isinstance(other, self.__class__):
            return self.identifier == other.identifier
        return False

    def __str__(self):
        """Return a string representation of this object."""
        services = [' - {0}'.format(s) for s in self._services.values()]
        identifiers = [' - {0}'.format(x) for x in self.all_identifiers]
        return '       Name: {0}\n' \
               '    Address: {1}\n' \
               'Identifiers:\n' \
               '{2}\n' \
               'Services:\n' \
               '{3}'.format(self.name, self.address,
                            '\n'.join(identifiers), '\n'.join(services))


# pylint: disable=too-few-public-methods
class BaseService:
    """Base class for protocol services."""

    def __init__(self, identifier, protocol, port):
        """Initialize a new BaseService."""
        self.__identifier = identifier
        self.protocol = protocol
        self.port = port
        self.credentials = None

    @property
    def identifier(self):
        """Return unique identifier associated with this service."""
        return self.__identifier

    def merge(self, other):
        """Merge with other service of same type."""
        self.credentials = other.credentials or self.credentials

    def __str__(self):
        """Return a string representation of this object."""
        return 'Protocol: {0}, Port: {1}, Credentials: {2}'.format(
            convert.protocol_str(self.protocol), self.port,
            self.credentials)


# pylint: disable=too-few-public-methods
class DmapService(BaseService):
    """Representation of a DMAP service."""

    def __init__(self, identifier, credentials, port=None):
        """Initialize a new DmapService."""
        super().__init__(identifier, PROTOCOL_DMAP, port or 3689)
        self.credentials = credentials


# pylint: disable=too-few-public-methods
class MrpService(BaseService):
    """Representation of a MediaRemote Protocol service."""

    def __init__(self, identifier, port, credentials=None):
        """Initialize a new MrpService."""
        super().__init__(identifier, PROTOCOL_MRP, port)
        self.credentials = credentials


# pylint: disable=too-few-public-methods
class AirPlayService(BaseService):
    """Representation of an AirPlay service."""

    def __init__(self, identifier, port=7000, credentials=None):
        """Initialize a new AirPlayService."""
        super().__init__(identifier, PROTOCOL_AIRPLAY, port)
        self.credentials = credentials
