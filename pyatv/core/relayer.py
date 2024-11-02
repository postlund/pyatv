"""Relay method calls to interfaces of multiple implementations.

A Relayer instance keeps track of multiple subclasses of an interface and forwards
method calls to one of the instances based on a priority list. Using this example:

* Metadata
  - DmapMetadata
  - MrpMetadata
  - CompanionMetadata
  - AirPlayMetadata

If all of these protocols were available, the general priority order would likely be
MrpMetadata, DmapMetadata, AirPlayMetadata, CompanionMetadata (the last two currently
does not support metadata). So the relayer would first and foremost call a method in
MrpMetadata, then DmapMetadata if no implementation exists, and so on. If no instance
provides an implementation, an `exceptions.NotSupportedError` is raised.

A code example:

relayer = Relayer(
    interface.Metadata,
    [MrpMetadata, DmapMetadata, CompanionMetadata, AirPlayMetadata]
)
relayer.register(MrpMetadata())
relayer.register(DmapMetadata())
relayer.register(CompanionMetadata())
relayer.register(AirPlayMetadata())
artwork = await relayer.relay("artwork")(width=640)
"""

from itertools import chain
from typing import Dict, Generic, List, Optional, Sequence, Type, TypeVar

from pyatv import exceptions
from pyatv.const import Protocol

T = TypeVar("T")


class Relayer(Generic[T]):
    """Relay method calls to instances based on priority."""

    def __init__(
        self, base_interface: Type[T], protocol_priority: List[Protocol]
    ) -> None:
        """Initialize a new Relayer instance."""
        self._base_interface = base_interface
        self._priorities = protocol_priority
        self._interfaces: Dict[Protocol, T] = {}
        self._takeover_protocol: List[Protocol] = []

    @property
    def count(self):
        """Return number of registered instances."""
        return len(self._interfaces)

    @property
    def main_instance(self) -> T:
        """Return main instance based on priority."""
        for priority in chain(self._takeover_protocol, self._priorities):
            if priority in self._interfaces:
                return self._interfaces[priority]
        raise exceptions.NotSupportedError()

    @property
    def main_protocol(self) -> Optional[Protocol]:
        """Return Protocol for main instance."""
        for priority in chain(self._takeover_protocol, self._priorities):
            if priority in self._interfaces:
                return priority
        return None

    @property
    def instances(self) -> Sequence[T]:
        """Return all instances added to this relayer."""
        return list(self._interfaces.values())

    def register(self, instance: T, protocol: Protocol) -> None:
        """Register a new instance for an interface."""
        if protocol not in self._priorities:
            raise RuntimeError(f"{protocol} not in priority list")

        self._interfaces[protocol] = instance

    def get(self, protocol: Protocol) -> Optional[T]:
        """Return instance for protocol if available."""
        return self._interfaces.get(protocol)

    def relay(self, target: str, priority: Optional[List[Protocol]] = None):
        """Return method (or property value) of target instance based on priority."""
        instance = self._find_instance(
            target, chain(self._takeover_protocol, priority or self._priorities)
        )
        return getattr(instance, target)

    def _find_instance(self, target: str, priority):
        for priority_iface in priority:
            interface = self._interfaces.get(priority_iface)

            # Interface defined in priority list but no instance for that interface
            # are just ignored as no implementation probably exists
            if not interface:
                continue

            # Trying to call a method not in the target interface
            relay_target = getattr(type(interface), target, None)
            if not relay_target:
                raise RuntimeError(f"{target} not in {priority_iface}")

            # Method must be overridden in base interface
            if relay_target != getattr(self._base_interface, target):
                return interface

        # An existing method not implemented by any instance is "not supported"
        raise exceptions.NotSupportedError(f"{target} is not supported")

    def takeover(self, protocol: Protocol) -> None:
        """Temporary override priority list with a specific protocol."""
        if self._takeover_protocol:
            raise exceptions.InvalidStateError(
                f"{self._takeover_protocol[0]} has already done takeover"
            )
        self._takeover_protocol = [protocol]

    def release(self) -> None:
        """Release temporary takeover."""
        self._takeover_protocol = []
