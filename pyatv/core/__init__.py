"""Core module of pyatv."""
import asyncio
from typing import Any, Awaitable, Callable, Dict, Mapping, NamedTuple, Optional, Set

from pyatv.const import FeatureName, Protocol
from pyatv.interface import BaseService


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
    ) -> None:
        """Initialize a new MutableService."""
        super().__init__(identifier, protocol, port, properties, credentials, password)
        self._requires_password = False

    @property
    def requires_password(self) -> bool:
        """Return if a password is required to access service."""
        return self._requires_password

    @requires_password.setter
    def requires_password(self, value: bool) -> None:
        """Change if password is required or not."""
        self._requires_password = value


class SetupData(NamedTuple):
    """Information for setting up a protocol."""

    protocol: Protocol
    connect: Callable[[], Awaitable[bool]]
    close: Callable[[], Set[asyncio.Task]]
    device_info: Callable[[], Dict[str, Any]]
    interfaces: Mapping[Any, Any]
    features: Set[FeatureName]
