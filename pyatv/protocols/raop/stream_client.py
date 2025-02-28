"""Client for AirPlay audio streaming.

This is a "generic" client designed around how AirPlay works in regards to streaming.
The client uses an underlying "protocol" for protocol specific bits, i.e. to support
AirPlay v1 and/or v2. This is mainly for code reuse purposes.
"""

from abc import ABC, abstractmethod
import asyncio
import logging
from time import monotonic, monotonic_ns
from typing import Any, Dict, Mapping, NamedTuple, Optional, Tuple, cast
import weakref

from pyatv import exceptions
from pyatv.protocols.airplay.utils import pct_to_dbfs
from pyatv.protocols.raop import timing
from pyatv.protocols.raop.audio_source import AudioSource
from pyatv.protocols.raop.fifo import PacketFifo
from pyatv.protocols.raop.packets import (
    AudioPacketHeader,
    RetransmitReqeust,
    SyncPacket,
)
from pyatv.protocols.raop.parsers import (
    EncryptionType,
    MetadataType,
    get_audio_properties,
    get_encryption_types,
    get_metadata_types,
)
from pyatv.protocols.raop.protocols import StreamContext, StreamProtocol, TimingServer
from pyatv.settings import Settings
from pyatv.support import log_binary
from pyatv.support.metadata import EMPTY_METADATA, MediaMetadata
from pyatv.support.rtsp import FRAMES_PER_PACKET, RtspSession

_LOGGER = logging.getLogger(__name__)

# When being late, compensate by sending at most these many packets to catch up
MAX_PACKETS_COMPENSATE = 3

# We should store this many packets in case retransmission is requested
PACKET_BACKLOG_SIZE = 1000

# Number of "too slow to keep up" warnings to suppress before warning about them
SLOW_WARNING_THRESHOLD = 5

# Metadata used when no metadata is present
MISSING_METADATA = MediaMetadata(
    title="Streaming with pyatv", artist="pyatv", album="AirPlay", duration=0.0
)

SUPPORTED_ENCRYPTIONS = EncryptionType.Unencrypted | EncryptionType.MFiSAP


class PlaybackInfo(NamedTuple):
    """Information for what is currently playing."""

    metadata: MediaMetadata
    position: float


class ControlClient(asyncio.Protocol):
    """Control client responsible for e.g. sync packets."""

    def __init__(self, context: StreamContext, packet_backlog: PacketFifo):
        """Initialize a new ControlClient."""
        self.transport = None
        self.context = context
        self.packet_backlog = packet_backlog
        self.task: Optional[asyncio.Future] = None

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

        async def _sync_handler():
            try:
                await self._sync_task((addr, self.context.control_port))
            except asyncio.CancelledError:
                pass
            except Exception:
                _LOGGER.exception("control task failure")
            _LOGGER.debug("Periodic sync task ended")

        if self.task:
            raise RuntimeError("already running")

        self.task = asyncio.ensure_future(_sync_handler())

    async def _sync_task(self, dest: Tuple[str, int]):
        if self.transport is None:
            raise RuntimeError("socket not connected")

        first_packet = True
        current_time = timing.ts2ntp(self.context.head_ts, self.context.sample_rate)
        while self.transport is not None:
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

            log_binary(
                _LOGGER,
                "Sending sync packet",
                SyncPacket=packet,
                Sec=current_sec,
                Frac=current_frac,
                RtpTime=self.context.rtptime,
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

    def datagram_received(self, data, addr):
        """Handle incoming control data."""
        actual_type = data[1] & 0x7F  # Remove marker bit

        if actual_type == 0x55:
            self._retransmit_lost_packets(RetransmitReqeust.decode(data), addr)
        else:
            _LOGGER.debug("Received unhandled control data from %s: %s", addr, data)

    def _retransmit_lost_packets(self, request, addr):
        _LOGGER.debug("%s from %s", request, addr)

        for i in range(request.lost_packets):
            if request.lost_seqno + i in self.packet_backlog:
                packet = self.packet_backlog[request.lost_seqno + i]

                # Very "low level" here just because it's simple and avoids
                # unnecessary conversions
                original_seqno = packet[2:4]
                resp = b"\x80\xd6" + original_seqno + packet

                if self.transport:
                    self.transport.sendto(resp, addr)
            else:
                _LOGGER.debug("Packet %d not in backlog", request.lost_seqno + 1)

    @staticmethod
    def error_received(exc):
        """Handle a connection error."""
        _LOGGER.error("Control connection error: %s", exc)

    def connection_lost(self, exc):
        """Handle that connection was lost."""
        _LOGGER.debug("Control connection lost (%s)", exc)
        if self.task:
            self.task.cancel()
            self.task = None


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


class RaopListener(ABC):
    """Listener interface for RAOP state changes."""

    @abstractmethod
    def playing(self, playback_info: PlaybackInfo) -> None:
        """Media started playing with metadata."""

    @abstractmethod
    def stopped(self) -> None:
        """Media stopped playing."""


class StreamClient:
    """Simple client to stream audio."""

    def __init__(
        self,
        rtsp: RtspSession,
        context: StreamContext,
        protocol: StreamProtocol,
        settings: Settings,
    ):
        """Initialize a new StreamClient instance."""
        self.loop = asyncio.get_event_loop()
        self.rtsp: RtspSession = rtsp
        self.context: StreamContext = context
        self.settings: Settings = settings
        self.control_client: Optional[ControlClient] = None
        self.timing_server: Optional[TimingServer] = None
        self._packet_backlog: PacketFifo = PacketFifo(PACKET_BACKLOG_SIZE)
        self._encryption_types: EncryptionType = EncryptionType.Unknown
        self._metadata_types: MetadataType = MetadataType.NotSupported
        self._metadata: MediaMetadata = EMPTY_METADATA
        self._listener: Optional[weakref.ReferenceType[Any]] = None
        self._info: Dict[str, object] = {}
        self._properties: Mapping[str, str] = {}
        self._is_playing: bool = False
        self._protocol: StreamProtocol = protocol

    @property
    def listener(self):
        """Return current listener."""
        if self._listener is None:
            return None
        return self._listener()

    @listener.setter
    def listener(self, new_listener):
        """Change current listener."""
        if new_listener is not None:
            self._listener = weakref.ref(new_listener)
        else:
            self._listener = None

    @property
    def playback_info(self) -> PlaybackInfo:
        """Return current playback information."""
        metadata = (
            MISSING_METADATA if self._metadata == EMPTY_METADATA else self._metadata
        )
        return PlaybackInfo(metadata, self.context.position)

    @property
    def info(self) -> Dict[str, object]:
        """Return value mappings for server /info values."""
        return self._info

    def close(self):
        """Close session and free up resources."""
        self._protocol.teardown()
        if self.control_client:
            self.control_client.close()
        if self.timing_server:
            self.timing_server.close()

    async def initialize(self, properties: Mapping[str, str]):
        """Initialize the session."""
        self._properties = properties
        self._encryption_types = get_encryption_types(properties)
        self._metadata_types = get_metadata_types(properties)

        _LOGGER.debug(
            "Initializing RTSP with encryption=%s, metadata=%s",
            self._encryption_types,
            self._metadata_types,
        )

        # Misplaced check that unencrypted data is supported
        intersection = self._encryption_types & SUPPORTED_ENCRYPTIONS
        if not intersection or intersection == EncryptionType.Unknown:
            _LOGGER.debug("No supported encryption type, continuing anyway")

        self._update_output_properties(properties)

        (_, control_client) = await self.loop.create_datagram_endpoint(
            lambda: ControlClient(self.context, self._packet_backlog),
            local_addr=(
                self.rtsp.connection.local_ip,
                self.settings.protocols.raop.control_port,
            ),
        )
        (_, timing_server) = await self.loop.create_datagram_endpoint(
            TimingServer,
            local_addr=(
                self.rtsp.connection.local_ip,
                self.settings.protocols.raop.timing_port,
            ),
        )

        self.control_client = cast(ControlClient, control_client)
        self.timing_server = cast(TimingServer, timing_server)

        _LOGGER.debug(
            "Local ports: control=%d, timing=%d",
            self.control_client.port,
            self.timing_server.port,
        )

        self._info.update(await self.rtsp.info())
        _LOGGER.debug("Updated info parameters to: %s", self.info)

        # Handle some special authentication cases
        if self._requires_auth_setup:
            await self.rtsp.auth_setup()

        # Set up the streaming session
        await self._protocol.setup(self.timing_server.port, self.control_client.port)

    def _update_output_properties(self, properties: Mapping[str, str]) -> None:
        (
            self.context.sample_rate,
            self.context.channels,
            self.context.bytes_per_channel,
        ) = get_audio_properties(properties)
        _LOGGER.debug(
            "Update play settings to %d/%d/%dbit",
            self.context.sample_rate,
            self.context.channels,
            self.context.bytes_per_channel * 8,
        )

    @property
    def _requires_auth_setup(self):
        # Do auth-setup if MFiSAP encryption is supported by receiver. Also,
        # at least for now, only do this for AirPort Express as some receivers
        # won't play audio if setup process isn't finished:
        # https://github.com/postlund/pyatv/issues/1134
        model_name = self._properties.get("am", "")
        return (
            EncryptionType.MFiSAP in self._encryption_types
            and model_name.startswith("AirPort")
        )

    def stop(self):
        """Stop what is currently playing."""
        _LOGGER.debug("Stopping audio playback")
        self._is_playing = False

    async def set_volume(self, volume: float) -> None:
        """Change volume on the receiver."""
        await self.rtsp.set_parameter("volume", str(volume))
        self.context.volume = volume

    async def send_audio(  # pylint: disable=too-many-branches
        self,
        source: AudioSource,
        metadata: MediaMetadata = EMPTY_METADATA,
        /,
        volume: Optional[float] = None
    ):
        """Send an audio stream to the device."""
        if self.control_client is None or self.timing_server is None:
            raise RuntimeError("not initialized")

        self.context.reset()

        transport = None
        try:
            # Create a socket used for writing audio packets (ugly)
            transport, _ = await self.loop.create_datagram_endpoint(
                AudioProtocol,
                remote_addr=(self.rtsp.connection.remote_ip, self.context.server_port),
            )

            # Start sending sync packets
            self.control_client.start(self.rtsp.connection.remote_ip)

            # Send progress if supported by receiver
            if MetadataType.Progress in self._metadata_types:
                start = self.context.rtptime
                now = self.context.rtptime
                end = start + source.duration * self.context.sample_rate
                await self.rtsp.set_parameter("progress", f"{start}/{now}/{end}")

            # Apply text metadata if it is supported
            self._metadata = metadata
            if MetadataType.Text in self._metadata_types:
                _LOGGER.debug("Playing with metadata: %s", self.playback_info.metadata)
                await self.rtsp.set_metadata(
                    self.context.rtsp_session,
                    self.context.rtpseq,
                    self.context.rtptime,
                    self.playback_info.metadata,
                )

            # Send artwork if that is supported
            if (
                MetadataType.Artwork in self._metadata_types
                and metadata.artwork is not None
            ):
                _LOGGER.debug("Sending %s bytes artwork", len(metadata.artwork))
                await self.rtsp.set_artwork(
                    self.context.rtsp_session,
                    self.context.rtpseq,
                    self.context.rtptime,
                    metadata.artwork,
                )

            # Start keep-alive task to ensure connection is not closed by remote device
            await self._protocol.start_feedback()

            listener = self.listener
            if listener:
                listener.playing(self.playback_info)

            # Start playback
            await self.rtsp.record()

            await self.rtsp.flush(
                headers={
                    "Range": "npt=0-",
                    "Session": self.context.rtsp_session,
                    "RTP-Info": (
                        f"seq={self.context.rtpseq};rtptime={self.context.rtptime}"
                    ),
                }
            )

            if volume:
                await self.set_volume(pct_to_dbfs(volume))

            await self._stream_data(source, transport)
        except (  # pylint: disable=try-except-raise
            exceptions.ProtocolError,
            exceptions.AuthenticationError,
        ):
            raise  # Re-raise internal exceptions to maintain a proper stack trace
        except Exception as ex:
            raise exceptions.ProtocolError("an error occurred during streaming") from ex
        finally:
            self._packet_backlog.clear()  # Don't keep old packets around (big!)
            if transport:
                # TODO: Teardown should not be done here. In fact, nothing should be
                # closed here since the connection should be reusable for streaming
                # more audio files. Refactor when support for that is added.
                await self.rtsp.teardown(self.context.rtsp_session)
                transport.close()
            self._protocol.teardown()
            self.close()

            listener = self.listener
            if listener:
                listener.stopped()

    async def _stream_data(  # pylint: disable=too-many-locals
        self, source: AudioSource, transport
    ):
        stats = Statistics(self.context.sample_rate)

        initial_time = monotonic()
        self._is_playing = True
        prev_slow_seqno = None
        number_slow_seqno = 0
        while self._is_playing:
            current_seqno = self.context.rtpseq - 1

            num_sent = await self._send_packet(
                source, stats.total_frames == 0, transport
            )
            if num_sent == 0:
                break

            stats.tick(num_sent)
            frames_behind = stats.frames_behind

            # If we are late, send some additional frames with hopes of catching up
            if frames_behind >= FRAMES_PER_PACKET:
                max_packets = min(
                    int(frames_behind / FRAMES_PER_PACKET), MAX_PACKETS_COMPENSATE
                )
                _LOGGER.debug(
                    "Compensating with %d packets (%d frames behind)",
                    max_packets,
                    frames_behind,
                )
                num_sent, has_more_packets = await self._send_number_of_packets(
                    source, transport, max_packets
                )
                stats.tick(num_sent)
                if not has_more_packets:
                    break

            # Log how long it took to send sample_rate amount of frames (should be
            # one second).
            if stats.interval_completed:
                interval_time, interval_frames = stats.new_interval()
                _LOGGER.debug(
                    "Sent %d frames in %fs (current frames: %d, expected: %d)",
                    interval_frames,
                    interval_time,
                    stats.total_frames,
                    stats.expected_frame_count,
                )

            # Calculate the actual absolute position in stream and where we actually
            # are (from when we initially stared to stream). The diff is the time we
            # need to sleep until next lap.
            abs_time_stream = stats.total_frames / self.context.sample_rate
            rel_to_start = monotonic() - initial_time
            diff = abs_time_stream - rel_to_start
            if diff > 0:
                number_slow_seqno = 0
                await asyncio.sleep(diff)
            else:
                # Increase number of consecutive frames that we are late
                if prev_slow_seqno == current_seqno - 1:
                    number_slow_seqno += 1

                # Log warning if we reached threshold value
                if number_slow_seqno >= SLOW_WARNING_THRESHOLD:
                    log_method = _LOGGER.warning
                else:
                    log_method = _LOGGER.debug

                log_method(
                    "Too slow to keep up for seqno %d (%f vs %f => %f)",
                    current_seqno,
                    abs_time_stream,
                    rel_to_start,
                    diff,
                )
                prev_slow_seqno = current_seqno

        _LOGGER.debug(
            "Audio finished sending in %fs",
            (monotonic_ns() - stats.start_time_ns) / 10**9,
        )

    async def _send_packet(
        self, source: AudioSource, first_packet: bool, transport
    ) -> int:
        # Once all frames in the audio stream have been sent, we are still "latency"
        # behind and will start sending padding (empty audio) until we catch up. This
        # is needed to keep the sync packets in line with real time.
        if self.context.padding_sent >= self.context.latency:
            return 0

        frames = await source.readframes(FRAMES_PER_PACKET)
        if not frames:
            # No more frames to send means we send padding packets (just zeros) to keep
            # sync packets accurate
            # TODO: Cache empty packet as this is unnecessarily expensive
            frames = self.context.packet_size * b"\x00"
            self.context.padding_sent += int(len(frames) / self.context.frame_size)
        elif len(frames) != self.context.packet_size:
            # The audio stream length seldom aligns with number of frames per packet,
            # so pad the last packet with zeros
            frames += (self.context.packet_size - len(frames)) * b"\x00"

        header = AudioPacketHeader.encode(
            0x80,
            0xE0 if first_packet else 0x60,
            self.context.rtpseq,
            self.context.rtptime,
            self.rtsp.session_id,
        )

        audio = frames

        if transport.is_closing():
            _LOGGER.warning("Connection closed while streaming audio")
            return 0

        # Send packet and add it to backlog
        rtpseq, packet = await self._protocol.send_audio_packet(
            transport, header, audio
        )
        self._packet_backlog[rtpseq] = packet

        self.context.rtpseq = (self.context.rtpseq + 1) % (2**16)
        self.context.head_ts += int(len(frames) / self.context.frame_size)

        return int(len(frames) / self.context.frame_size)

    async def _send_number_of_packets(
        self, source: AudioSource, transport, count: int
    ) -> Tuple[int, bool]:
        """Send a specific number of packets.

        Return total number of sent frames and if more frames are available.
        """
        total_frames = 0
        for _ in range(count):
            sent = await self._send_packet(source, False, transport)
            total_frames += sent
            if sent == 0:
                return total_frames, False
        return total_frames, True


class Statistics:
    """Maintains statistics of frames during a streaming session."""

    def __init__(self, sample_rate: int):
        """Initialize a new Statistics instance."""
        self.sample_rate: int = sample_rate
        self.start_time_ns: int = monotonic_ns()
        self.interval_time: float = monotonic()
        self.total_frames: int = 0
        self.interval_frames: int = 0

    @property
    def expected_frame_count(self) -> int:
        """Number of frames expected to be sent at current time."""
        return int((monotonic_ns() - self.start_time_ns) / (10**9 / self.sample_rate))

    @property
    def frames_behind(self) -> int:
        """Number of frames behind until being in sync."""
        return self.expected_frame_count - self.total_frames

    @property
    def interval_completed(self) -> bool:
        """Return if an interval has completed.

        An interval has completed when sample_rate amount of frames
        has been sent since previous interval start.
        """
        return self.interval_frames >= self.sample_rate

    def tick(self, sent_frames: int):
        """Add newly sent frames to statistics."""
        self.total_frames += sent_frames
        self.interval_frames += sent_frames

    def new_interval(self) -> Tuple[float, int]:
        """Start measuring a new time interval."""
        end_time = monotonic()
        diff = end_time - self.interval_time
        self.interval_time = end_time

        frames = self.interval_frames
        self.interval_frames = 0

        return diff, frames
