"""Stub for the zeroconf library.

As zeroconf does not provide a stub or mock, this implementation will serve as
stub here. It can fake immediate answers for any service.
"""
from aiozeroconf import ServiceInfo


def homesharing_service(service_name, atv_name, address, hsgid):
    """Create a new home sharing service simulating an Apple TV."""
    # Mostly default values here for now
    props = {
        b'DFID': b'2', b'PrVs': b'65538', b'hG': hsgid, b'Name': atv_name,
        b'txtvers': b'1', b'atSV': b'65541', b'MiTPV': b'196611',
        b'EiTS': b'1', b'fs': b'2', b'MniT': b'167845888'
    }

    return ServiceInfo('_appletv-v2._tcp.local.',
                       service_name + '._appletv-v2._tcp.local.',
                       address=address, port=3689,
                       properties=props)


def mrp_service(service_name, atv_name, address, identifier, port=49152):
    """Create a MediaRemote service simulating an Apple TV."""
    props = {
        b'ModelName': b'Mac', b'SystemBuildVersion': b'16G29',
        b'Name': atv_name, b'AllowPairing': b'YES',
        b'UniqueIdentifier': identifier.encode('utf-8')
    }

    return ServiceInfo('_mediaremotetv._tcp.local.',
                       service_name + '._mediaremotetv._tcp.local.',
                       address=address, port=port,
                       properties=props)


def airplay_service(atv_name, address, deviceid, port=7000):
    """Create a MediaRemote service simulating an Apple TV."""
    props = {
        b'deviceid': deviceid.encode('utf-8'), b'model': b'AppleTV3,1',
        b'pi': b'4EE5AF58-7E5D-465A-935E-82E4DB74385D', b'flags': b'0x44',
        b'vv': b'2', b'features': b'0x5A7FFFF7,0xE',
        b'pk': b'3853c0e2ce3844727ca0cb1b86a3e3875e66924d2648d8f8caf71f8118793d98',  # noqa
        b'srcvers': b'220.68'
    }

    return ServiceInfo('_airplay._tcp.local.',
                       atv_name + '._airplay._tcp.local.',
                       address=address, port=port,
                       properties=props)


def device_service(service_name, atv_name, address):
    """Create a service representing an Apple TV with no home-sharing."""
    props = {
        b'DvTy': b'AppleTV', b'Ver': b'131077', b'DvSv': b'1792',
        b'atCV': b'65539', b'atSV': b'65541', b'txtvers': b'1',
        b'DbId': b'AAAAAAAAAAAAAAAA', b'CtlN': atv_name
    }

    return ServiceInfo('_touch-able._tcp.local.',
                       service_name + '._touch-able._tcp.local.',
                       address=address, port=3689,
                       server='AppleTV-2.local.',
                       properties=props)


class ServiceBrowserStub:
    """Stub for ServiceBrowser."""

    def __init__(self, zeroconf, service_type, listener):
        """Create a new instance of ServiceBrowser."""
        for service in zeroconf.services:
            if service.type == service_type:
                listener.add_service(zeroconf, service_type, service.name)


class ZeroconfStub:
    """Stub for Zeroconf."""

    def __init__(self, services):
        """Create a new instance of Zeroconf."""
        self.services = services
        self.registered_services = []

    async def get_service_info(self, service_type, service_name, timeout=2000):
        """Look up service information."""
        for service in self.services:
            if service.name == service_name:
                return service

    async def register_service(self, service):
        """Save services registered services."""
        self.registered_services.append(service)

    async def unregister_service(self, service):
        """Stub for unregistering services (does nothing)."""
        pass

    async def close(self):
        """Stub for closing zeroconf (does nothing)."""
        pass


def stub(module, *services):
    """Stub a module using zeroconf."""
    instance = ZeroconfStub(list(services))
    module.Zeroconf = lambda loop, address_family=None: instance
    module.ServiceBrowser = ServiceBrowserStub
    return instance
