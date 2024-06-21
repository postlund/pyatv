"""Base classes used by streaming protocols."""

from abc import ABC, abstractmethod
import asyncio
import logging
from random import randrange
from typing import Optional, Tuple

from pyatv.auth.hap_pairing import NO_CREDENTIALS, HapCredentials
from pyatv.protocols.raop import timing
from pyatv.protocols.raop.packets import TimingPacket
from pyatv.support.rtsp import FRAMES_PER_PACKET

_LOGGER = logging.getLogger(__name__)


class StreamContext:
    """Data used for one RAOP session."""

    def __init__(self) -> None:
        """Initialize a new StreamContext."""
        self.credentials: HapCredentials = NO_CREDENTIALS
        self.password: Optional[str] = None

        self.sample_rate: int = 44100
        self.channels: int = 2
        self.bytes_per_channel: int = 2
        self.latency = 22050 + self.sample_rate

        self.rtpseq: int = 0
        self.start_ts = 0
        self.head_ts = 0
        self.padding_sent: int = 0

        self.server_port: int = 0
        self.event_port: int = 0
        self.control_port: int = 0
        self.timing_port: int = 0
        self.rtsp_session: int = 0

        self.volume: Optional[float] = None

    def reset(self) -> None:
        """Reset seasion.

        Must be done when sample rate changes.
        """
        self.rtpseq = randrange(2**16)
        self.start_ts = timing.ntp2ts(timing.ntp_now(), self.sample_rate)
        self.head_ts = self.start_ts
        self.latency = 22050 + self.sample_rate
        self.padding_sent = 0

    @property
    def rtptime(self) -> int:
        """Current RTP time with latency."""
        return self.head_ts - (self.start_ts - self.latency)

    @property
    def position(self) -> float:
        """Current position in stream (seconds with fraction)."""
        # Do not consider latency here (so do not use rtptime)
        return timing.ts2ms(self.head_ts - self.start_ts, self.sample_rate) / 1000.0

    @property
    def frame_size(self) -> int:
        """Size of a single audio frame."""
        return self.channels * self.bytes_per_channel

    @property
    def packet_size(self) -> int:
        """Size of a full audio packet."""
        return FRAMES_PER_PACKET * self.frame_size


class StreamProtocol(ABC):
    """Base interface for a streaming protocol."""

    @abstractmethod
    async def setup(self, timing_server_port: int, control_client_port: int) -> None:
        """To setup connection prior to starting to stream."""

    @abstractmethod
    def teardown(self) -> None:
        """Teardown resources allocated by setup efter streaming finished."""

    @abstractmethod
    async def start_feedback(self) -> None:
        """Start to send feedback (if supported and required)."""

    @abstractmethod
    async def send_audio_packet(
        self, transport: asyncio.DatagramTransport, rtp_header: bytes, audio: bytes
    ) -> Tuple[int, bytes]:
        """Send audio packet to receiver."""

    @abstractmethod
    async def play_url(self, timing_server_port: int, url: str, position: float = 0.0):
        """Play media from a URL."""


class TimingServer(asyncio.Protocol):
    """Basic timing server responding to timing requests."""

    def __init__(self):
        """Initialize a new TimingServer."""
        self.transport = None

    def close(self):
        """Close timing server."""
        if self.transport:
            self.transport.close()
            self.transport = None

    @property
    def port(self):
        """Port this server listens to."""
        return self.transport.get_extra_info("socket").getsockname()[1]

    def connection_made(self, transport):
        """Handle that connection succeeded."""
        self.transport = transport

    def datagram_received(self, data, addr):
        """Handle incoming timing requests."""
        req = TimingPacket.decode(data)
        recvtime_sec, recvtime_frac = timing.ntp2parts(timing.ntp_now())
        resp = TimingPacket.encode(
            req.proto,
            0x53 | 0x80,
            7,
            0,
            req.sendtime_sec,
            req.sendtime_frac,
            recvtime_sec,
            recvtime_frac,
            recvtime_sec,
            recvtime_frac,
        )
        self.transport.sendto(resp, addr)

    @staticmethod
    def error_received(exc) -> None:
        """Handle a connection error."""
        _LOGGER.error("Error received: %s", exc)
