"""Core module of pyatv."""
import asyncio
from typing import Any, Awaitable, Callable, Dict, Mapping, NamedTuple, Optional, Set

from pyatv.const import FeatureName, PairingRequirement, Protocol
from pyatv.interface import BaseService

TakeoverMethod = Callable[
    ...,
    Callable[[], None],
]


class MutableService(BaseService):
    """Mutable version of BaseService allowing some fields to be changed.

    This is an internal implementation of BaseService that allows protocols to change
    some fields during set up. The mutable property is not exposed outside of core.
    """

    def __init__(
        self,
        identifier: Optional[str],
        protocol: Protocol,
        port: int,
        properties: Optional[Mapping[str, str]],
        credentials: Optional[str] = None,
        password: Optional[str] = None,
        enabled: bool = True,
    ) -> None:
        """Initialize a new MutableService."""
        super().__init__(
            identifier, protocol, port, properties, credentials, password, enabled
        )
        self._requires_password = False
        self._pairing_requirement = PairingRequirement.Unsupported

    @property
    def requires_password(self) -> bool:
        """Return if a password is required to access service."""
        return self._requires_password

    @requires_password.setter
    def requires_password(self, value: bool) -> None:
        """Change if password is required or not."""
        self._requires_password = value

    @property
    def pairing(self) -> PairingRequirement:
        """Return if pairing is required by service."""
        return self._pairing_requirement

    @pairing.setter
    def pairing(self, value: PairingRequirement) -> None:
        """Change if pairing is required by service."""
        self._pairing_requirement = value

    def __deepcopy__(self, memo) -> "BaseService":
        """Return deep-copy of instance."""
        copy = MutableService(
            self.identifier,
            self.protocol,
            self.port,
            self.properties,
            self.credentials,
            self.password,
            self.enabled,
        )
        copy.pairing = self.pairing
        copy.requires_password = self.requires_password
        return copy


class SetupData(NamedTuple):
    """Information for setting up a protocol."""

    protocol: Protocol
    connect: Callable[[], Awaitable[bool]]
    close: Callable[[], Set[asyncio.Task]]
    device_info: Callable[[], Dict[str, Any]]
    interfaces: Mapping[Any, Any]
    features: Set[FeatureName]
