"""Base class for HAP based channels (connections)."""
from abc import ABC, abstractmethod
import asyncio
import logging
from typing import Callable, Optional, Tuple, cast

from pyatv import exceptions
from pyatv.auth.hap_pairing import PairVerifyProcedure
from pyatv.auth.hap_session import HAPSession
from pyatv.support import log_binary
from pyatv.support.state_producer import StateProducer

_LOGGER = logging.getLogger(__name__)


class AbstractHAPChannel(ABC, StateProducer, asyncio.Protocol):
    """Abstract base class for connections using HAP encryption and segmenting."""

    def __init__(self, output_key: bytes, input_key: bytes) -> None:
        """Initialize a new AbstractHAPChannel instance."""
        super().__init__()
        self.buffer: bytes = b""
        self.transport: Optional[asyncio.Transport] = None
        self.session: HAPSession = HAPSession()
        self.session.enable(output_key, input_key)

    @property
    def port(self) -> int:
        """Remote connection port number."""
        if self.transport is None:
            raise exceptions.InvalidStateError("not connected")

        sock = self.transport.get_extra_info("socket")
        _, dstport = sock.getpeername()
        return dstport

    def close(self) -> None:
        """Close the channel."""
        if self.transport:
            self.transport.close()
            self.transport = None

    def connection_made(self, transport) -> None:
        """Device connection was made."""
        sock = transport.get_extra_info("socket")
        dstaddr, dstport = sock.getpeername()
        _LOGGER.debug("Connected to %s:%d", dstaddr, dstport)

        self.transport = transport

    def data_received(self, data: bytes) -> None:
        """Message was received from device."""
        assert self.transport is not None

        log_binary(_LOGGER, "Received data", Data=data)
        decrypt = self.session.decrypt(data)
        if decrypt:
            self.buffer += decrypt
            self.handle_received()

    @abstractmethod
    def handle_received(self) -> None:
        """Handle received data that was put in buffer."""

    def send(self, data: bytes) -> None:
        """Send message to device."""
        assert self.transport is not None

        encrypted = self.session.encrypt(data)
        log_binary(_LOGGER, "Sending data", Encrypted=encrypted)
        self.transport.write(encrypted)

    def connection_lost(self, exc) -> None:
        """Device connection was dropped."""
        _LOGGER.debug("Connection was lost to remote")


async def setup_channel(
    factory: Callable[[bytes, bytes], AbstractHAPChannel],
    verifier: PairVerifyProcedure,
    address: str,
    port: int,
    salt: str,
    output_info: str,
    input_info: str,
) -> Tuple[asyncio.BaseTransport, AbstractHAPChannel]:
    """Set up a new HAP channel and enable encryption."""
    out_key, in_key = verifier.encryption_keys(salt, output_info, input_info)

    loop = asyncio.get_event_loop()
    transport, protocol = await loop.create_connection(
        lambda: factory(out_key, in_key),
        address,
        port,
    )
    return transport, cast(AbstractHAPChannel, protocol)
