"""Stub for the zeroconf library.

As zeroconf does not provide a stub or mock, this implementation will serve as
stub here. It can fake immediate answers for any service. Currently only the
home sharing service has been added.
"""

from zeroconf import ServiceInfo


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
                       address=address, port='3689',
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
                       address=address, port='3689',
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

    def get_service_info(self, service_type, service_name):
        """Look up service information."""
        for service in self.services:
            if service.name == service_name:
                return service

    def register_service(self, service):
        """Save services registered services."""
        self.registered_services.append(service)

    def unregister_service(self, service):
        """Stub for unregistering services (does nothing)."""
        pass

    def close(self):
        """Stub for closing zeroconf (does nothing)."""
        pass


def stub(module, *services):
    """Stub a module using zeroconf."""
    instance = ZeroconfStub(list(services))
    module.Zeroconf = lambda: instance
    module.ServiceBrowser = ServiceBrowserStub
    return instance
