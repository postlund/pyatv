"""Support for audio streaming using Remote Audio Output Protocol (RAOP)."""

import asyncio
import logging
from typing import Any, Awaitable, Callable, Dict, Set, Tuple, cast

from pyatv import conf, exceptions
from pyatv.const import FeatureName, FeatureState, Protocol
from pyatv.interface import FeatureInfo, Features, StateProducer, Stream
from pyatv.support.net import ClientSessionManager
from pyatv.support.relayer import Relayer

_LOGGER = logging.getLogger(__name__)


class RaopFeatures(Features):
    """Implementation of supported feature functionality."""

    def __init__(self, service: conf.RaopService) -> None:
        """Initialize a new RaopFeatures instance."""
        self.service = service

    def get_feature(self, feature_name: FeatureName) -> FeatureInfo:
        """Return current state of a feature."""
        if feature_name == FeatureName.StreamFile:
            return FeatureInfo(FeatureState.Available)

        return FeatureInfo(FeatureState.Unavailable)


class RaopStream(Stream):
    """Implementation of stream functionality."""

    def __init__(self, address: str, service: conf.RaopService) -> None:
        """Initialize a new RaopStream instance."""
        self.address = address
        self.service = service

    async def stream_file(self, filename: str, **kwargs) -> None:
        """Stream local file to device.

        INCUBATING METHOD - MIGHT CHANGE IN THE FUTURE!
        """
        raise exceptions.NotSupportedError()


def setup(
    loop: asyncio.AbstractEventLoop,
    config: conf.AppleTV,
    interfaces: Dict[Any, Relayer],
    device_listener: StateProducer,
    session_manager: ClientSessionManager,
) -> Tuple[Callable[[], Awaitable[None]], Callable[[], None], Set[FeatureName]]:
    """Set up a new RAOP service."""
    service = config.get_service(Protocol.RAOP)
    assert service is not None

    service = cast(conf.RaopService, service)

    interfaces[Stream].register(RaopStream(str(config.address), service), Protocol.RAOP)
    interfaces[Features].register(RaopFeatures(service), Protocol.RAOP)

    async def _connect() -> None:
        pass

    def _close() -> None:
        pass

    return _connect, _close, set([FeatureName.StreamFile])
