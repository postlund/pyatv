"""Implementation of a protocol in mocked version for testing.

This module allows for mocking protocols in pyatv.protocols and is meant for testing
core features. It is not complete, just implemented enough to work. More fine grained
functionality can be added over time as needed.
"""

from contextlib import contextmanager
from typing import Any, Dict, Generator, Mapping, Optional
from unittest.mock import AsyncMock, MagicMock, patch

from pyatv.const import Protocol
from pyatv.core import Core, MutableService
from pyatv.core.scan import ScanHandlerDeviceInfoName
from pyatv.interface import BaseService, DeviceInfo, PairingHandler
from pyatv.protocols import ProtocolMethods, SetupData


class MockedProtocol:
    def __init__(self, protocol: Protocol) -> None:
        self._protocol = protocol
        self.pair_mock = MagicMock(name=f"{self._protocol.name}_pairing_handler")
        self.setup_mock = self._create_setup_mock()
        self.core: Optional[Core] = None

    @property
    def methods(self) -> ProtocolMethods:
        return ProtocolMethods(
            self.setup, self.scan, self.pair, self.device_info, self.service_info
        )

    def _create_setup_mock(self):
        mock = MagicMock(f"_setup_mock")
        mock.connect = AsyncMock(return_value=True)
        mock.close = MagicMock(return_value=set())
        mock.device_info = MagicMock(return_value={})
        mock.interfaces = {}
        mock.features = []
        return mock

    def scan(self) -> Mapping[str, ScanHandlerDeviceInfoName]:
        """Return handlers used for scanning."""
        return {}

    def device_info(
        self, service_type: str, properties: Mapping[str, Any]
    ) -> Dict[str, Any]:
        """Return device information from Zeroconf properties."""

    async def service_info(
        self,
        service: MutableService,
        devinfo: DeviceInfo,
        services: Mapping[Protocol, BaseService],
    ) -> None:
        """Update service with additional information.

        If Home Sharing is enabled, then the "hG" property is present and can be used as
        credentials. If not enabled, then pairing must be performed.
        """

    def setup(self, core: Core) -> Generator[SetupData, None, None]:
        """Set up a new protocol service."""
        self.core = core
        yield SetupData(
            self._protocol,
            self.setup_mock.connect,
            self.setup_mock.close,
            self.setup_mock.device_info,
            self.setup_mock.interfaces,
            self.setup_mock.device_info,
        )

    def pair(self, core: Core, **kwargs) -> PairingHandler:
        """Return pairing handler for protocol."""
        self.core = core
        return self.pair_mock


@contextmanager
def mock_protocol(protocol: Protocol) -> MockedProtocol:
    protocol_mock = MockedProtocol(protocol)
    with patch.dict("pyatv.PROTOCOLS", {protocol: protocol_mock.methods}, clear=True):
        yield protocol_mock
