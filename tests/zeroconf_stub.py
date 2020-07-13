"""Stub for the zeroconf library.

As zeroconf does not provide a stub or mock, this implementation will serve as
stub here. It can fake immediate answers for any service.
"""
from zeroconf import ServiceInfo


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
