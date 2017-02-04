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


class ServiceBrowserStub:
    """Stub for ServiceBrowser."""

    def __init__(self, zeroconf, service_type, listener):
        """Create a new instance of ServiceBrowser."""
        for service in zeroconf.services:
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


instance = None


def stub(module, *services):
    """Stub a module using zeroconf."""
    def _zeroconf():
        global instance
        instance = ZeroconfStub(list(services))
        return instance

    module.Zeroconf = _zeroconf
    module.ServiceBrowser = ServiceBrowserStub
