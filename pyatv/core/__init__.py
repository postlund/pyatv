"""Core module of pyatv."""
import asyncio
from typing import Any, Awaitable, Callable, Dict, Mapping, NamedTuple, Set

from pyatv.const import FeatureName, Protocol


class SetupData(NamedTuple):
    """Information for setting up a protocol."""

    protocol: Protocol
    connect: Callable[[], Awaitable[bool]]
    close: Callable[[], Set[asyncio.Task]]
    device_info: Callable[[], Dict[str, Any]]
    interfaces: Mapping[Any, Any]
    features: Set[FeatureName]
