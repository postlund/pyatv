"""Support for RAOP (AirPlay v1)."""
import asyncio
import logging
from time import time
from typing import List, Mapping, Optional, Tuple
import wave

from bitarray import bitarray

from pyatv.raop import timing
from pyatv.raop.packets import AudioPacketHeader, SyncPacket, TimingPacket
from pyatv.raop.rtsp import FRAMES_PER_PACKET, RtspContext, RtspSession

_LOGGER = logging.getLogger(__name__)


class ControlClient(asyncio.Protocol):
    """Control client responsible for e.g. sync packets."""

    def __init__(self, context: RtspContext):
        """Initialize a new ControlClient."""
        self.transport = None
        self.context = context
        self.task: Optional[asyncio.Task] = None

    def close(self):
        """Close control client."""
        if self.transport:
            self.transport.close()
            self.transport = None

    @property
    def port(self):
        """Port this control client listens to."""
        return self.transport.get_extra_info("socket").getsockname()[1]

    def start(self, addr: str):
        """Start sending periodic sync messages."""
        _LOGGER.debug("Starting periodic sync task")

        async def _handler():
            try:
                await self._sync_task((addr, self.context.control_port))
            except Exception:
                _LOGGER.exception("control task failure")
            finally:
                _LOGGER.debug("Periodic sync task ended")

        if self.task:
            raise RuntimeError("already running")

        self.task = asyncio.create_task(_handler())

    async def _sync_task(self, dest: Tuple[str, int]):
        if self.transport is None:
            raise RuntimeError("socket not connected")

        first_packet = True
        current_time = timing.ts2ntp(self.context.head_ts, self.context.sample_rate)
        while True:
            current_sec, current_frac = timing.ntp2parts(current_time)
            packet = SyncPacket.encode(
                0x90 if first_packet else 0x80,
                0xD4,
                0x0007,
                self.context.rtptime - self.context.latency,
                current_sec,
                current_frac,
                self.context.rtptime,
            )

            first_packet = False
            self.transport.sendto(packet, dest)

            await asyncio.sleep(1.0)  # Very low granularity here
            current_time = timing.ts2ntp(self.context.head_ts, self.context.sample_rate)

    def stop(self):
        """Stop control client."""
        if self.task:
            self.task.cancel()
            self.task = None

    def connection_made(self, transport):
        """Handle that connection succeeded."""
        self.transport = transport

    @staticmethod
    def datagram_received(data, addr):
        """Handle incoming control data."""
        _LOGGER.debug("Received control data from %s: %s", addr, data)

    @staticmethod
    def error_received(exc):
        """Handle a connection error."""
        _LOGGER.error("Comtrol connection error: %s", exc)

    def connection_lost(self, exc):
        """Handle that connection was lost."""
        _LOGGER.debug("Control connection lost (%s)", exc)
        if self.task:
            self.task.cancel()
            self.task = None


class TimingClient(asyncio.Protocol):
    """Basic timing client responding to timing requests."""

    def __init__(self):
        """Initialize a new TimingClient."""
        self.transport = None

    def close(self):
        """Close timing client."""
        if self.transport:
            self.transport.close()
            self.transport = None

    @property
    def port(self):
        """Port this client listens to."""
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


class AudioProtocol(asyncio.Protocol):
    """Minimal protocol to send audio packets."""

    def __init__(self):
        """Initialize a new AudioProtocol instance."""
        self.transport = None

    def connection_made(self, transport):
        """Handle that connection succeeded."""
        self.transport = transport

    def datagram_received(self, data, addr):
        """Handle incoming data.

        No data should ever be seen here.
        """

    def error_received(self, exc) -> None:
        """Handle a connection error."""
        self.transport.close()
        _LOGGER.error("Audio error received: %s", exc)

    def connection_lost(self, exc):
        """Handle that connection was lost."""
        _LOGGER.debug("Audio connection lost (%s)", exc)


def parse_transport(transport: str) -> Tuple[List[str], Mapping[str, str]]:
    """Parse Transport header in SETUP response."""
    params = []
    options = {}
    for option in transport.split(";"):
        if "=" in option:
            key, value = option.split("=", maxsplit=1)
            options[key] = value
        else:
            params.append(option)
    return params, options


class RaopClient:
    """Simple RAOP client to stream audio."""

    def __init__(self, rtsp: RtspSession, context: RtspContext):
        """Initialize a new RaopClient instance."""
        self.loop = asyncio.get_event_loop()
        self.rtsp: RtspSession = rtsp
        self.context: RtspContext = context
        self.control_client: Optional[ControlClient] = None
        self.timing_client: Optional[TimingClient] = None

    def close(self):
        """Close session and free up resources."""
        self.rtsp.close()
        if self.control_client:
            self.control_client.close()
        if self.timing_client:
            self.timing_client.close()

    async def initialize(self):
        """Initialize the session."""
        loop = asyncio.get_event_loop()
        (_, self.control_client) = await loop.create_datagram_endpoint(
            lambda: ControlClient(self.context), local_addr=(self.rtsp.local_ip, 0)
        )
        (_, self.timing_client) = await loop.create_datagram_endpoint(
            TimingClient, local_addr=(self.rtsp.local_ip, 0)
        )

        _LOGGER.debug(
            "Local ports: control=%d, timing=%d",
            self.control_client.port,
            self.timing_client.port,
        )

    async def _setup_session(self):
        await self.rtsp.announce()

        resp = await self.rtsp.setup(self.control_client.port, self.timing_client.port)
        _, options = parse_transport(resp.headers["Transport"])
        self.context.timing_port = int(options.get("timing_port", 0))
        self.context.control_port = int(options["control_port"])
        self.context.rtsp_session = resp.headers["Session"]
        self.context.server_port = int(options["server_port"])

        _LOGGER.debug(
            "Remote ports: control=%d, timing=%d, server=%d",
            self.context.control_port,
            self.context.timing_port,
            self.context.server_port,
        )

        await self.rtsp.record(self.context.rtpseq, self.context.rtptime)

        # TODO: Should not be set here and allow custom values
        await self.rtsp.set_parameter("volume", "-20")

        rtptime = self.context.rtptime
        await self.rtsp.set_parameter(
            "progress",
            f"{rtptime}/{rtptime}/{rtptime+3*self.context.sample_rate}",
        )
        await self.rtsp.set_metadata(
            self.context.rtpseq, self.context.rtptime, "item", "album", "artist"
        )

    async def send_audio(self, wave_file):
        """Send an audio stream to the device."""
        if self.control_client is None or self.timing_client is None:
            raise Exception("not initialized")  # TODO: better exception

        transport = None
        try:
            # Update sample rate, channel count, etc. from stream
            self._update_context(wave_file)

            # Set up the streaming session
            await self._setup_session()

            # Create a socket used for writing audio packets (ugly)
            transport, _ = await self.loop.create_datagram_endpoint(
                AudioProtocol,
                remote_addr=(self.rtsp.remote_ip, self.context.server_port),
            )

            # Start sending sync packets
            self.control_client.start(self.rtsp.remote_ip)

            await self._stream_data(wave_file, transport)
        finally:
            if transport:
                transport.close()
            self.control_client.stop()

    def _update_context(self, wave_file: wave.Wave_read) -> None:
        self.context.sample_rate = wave_file.getframerate()
        self.context.channels = wave_file.getnchannels()
        self.context.bytes_per_channel = wave_file.getsampwidth()
        self.context.reset()
        _LOGGER.debug(
            "Update play settings to %d/%d/%dbit",
            self.context.sample_rate,
            self.context.channels,
            self.context.bytes_per_channel * 8,
        )

    async def _stream_data(self, wave_file: wave.Wave_read, transport):
        first_packet = True
        packets_per_second = self.context.sample_rate / FRAMES_PER_PACKET
        packet_interval = 1 / packets_per_second

        stream_start = time()
        while True:
            start_time = time()
            frames = wave_file.readframes(FRAMES_PER_PACKET)
            if not frames:
                break

            header = AudioPacketHeader.encode(
                0x80,
                0xE0 if first_packet else 0x60,
                self.context.rtpseq,
                self.context.rtptime,
                self.context.session_id,
            )

            # ALAC frame with raw data. Not so pretty but will work for now until a
            # proper ALAC encoder is added.
            audio = bitarray("00" + str(self.context.channels - 1) + 19 * "0" + "1")
            for i in range(0, len(frames), 2):
                audio.frombytes(bytes([frames[i + 1], frames[i]]))

            first_packet = False
            self.context.rtpseq = (self.context.rtpseq + 1) % (2 ** 16)
            self.context.head_ts += int(
                len(frames) / (self.context.channels * self.context.bytes_per_channel)
            )

            if not transport.is_closing():
                transport.sendto(header + audio.tobytes())
            else:
                _LOGGER.warning("Connection closed while streaming audio")
                break

            # Assuming processing isn't exceeding packet interval (i.e. we are
            # processing packets to slow), we should sleep for a while
            processing_time = time() - start_time
            if processing_time < packet_interval:
                await asyncio.sleep(packet_interval - processing_time)
            else:
                _LOGGER.warning(
                    "Too slow to keep up for seqno %d (%f > %f)",
                    self.context.rtpseq - 1,
                    processing_time,
                    packet_interval,
                )

        _LOGGER.debug("Audio finished sending in %fs", time() - stream_start)
        await asyncio.sleep(self.context.latency / self.context.sample_rate)
