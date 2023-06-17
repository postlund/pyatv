"""Implementation of AirPlay v2 protocol logic."""
import asyncio
import logging
from typing import Optional, Tuple
from uuid import uuid4

from pyatv.auth.hap_channel import setup_channel
from pyatv.protocols.airplay.auth import verify_connection
from pyatv.protocols.airplay.channels import EventChannel
from pyatv.protocols.raop.protocols import StreamContext, StreamProtocol
from pyatv.support.chacha20 import Chacha20Cipher
from pyatv.support.http import decode_bplist_from_body
from pyatv.support.rtsp import RtspSession

_LOGGER = logging.getLogger(__name__)

EVENTS_SALT = "Events-Salt"
EVENTS_WRITE_INFO = "Events-Write-Encryption-Key"
EVENTS_READ_INFO = "Events-Read-Encryption-Key"

FEEDBACK_INTERVAL = 2.0  # Seconds


class AirPlayV2(StreamProtocol):
    """Stream protocol used for AirPlay v1 support."""

    def __init__(self, context: StreamContext, rtsp: RtspSession) -> None:
        """Initialize a new AirPlayV2 instance."""
        super().__init__()
        self.context = context
        self.rtsp = rtsp
        self.event_channel: Optional[asyncio.BaseTransport] = None
        self._cipher: Optional[Chacha20Cipher] = None
        self._feedback_task: Optional[asyncio.Task] = None

    async def setup(self, timing_client_port: int, control_client_port: int) -> None:
        """To setup connection prior to starting to stream."""
        verifier = await verify_connection(
            self.context.credentials, self.rtsp.connection
        )

        setup_resp = await self.rtsp.setup(
            body={
                "deviceID": "AA:BB:CC:DD:EE:FF",
                "sessionUUID": str(uuid4()).upper(),
                "timingPort": timing_client_port,
                "timingProtocol": "NTP",
                "isMultiSelectAirPlay": True,
                "groupContainsGroupLeader": False,
                "macAddress": "AA:BB:CC:DD:EE:FF",
                "model": "iPhone14,3",
                "name": "pyatv",
                "osBuildVersion": "20F66",
                "osName": "iPhone OS",
                "osVersion": "16.5",
                "senderSupportsRelay": False,
                "sourceVersion": "690.7.1",
                "statsCollectionEnabled": False,
            }
        )
        resp = decode_bplist_from_body(setup_resp)
        _LOGGER.debug("Setup response body: %s", resp)

        event_port = resp.get("eventPort", 0)

        # This is a bit hacky, but I noticed that airplay2-receiver seems to set up the
        # event channel some time after responding with the port used for it. So the
        # connect call fails. By doing some retries here, it will work after some
        # attempts. So keeping that here for compatibility reason.
        retries = 5
        transport = None
        while transport is None:
            try:
                transport, _ = await setup_channel(
                    EventChannel,
                    verifier,
                    self.rtsp.connection.remote_ip,
                    event_port,
                    EVENTS_SALT,
                    EVENTS_READ_INFO,
                    EVENTS_WRITE_INFO,
                )
            except ConnectionRefusedError:
                retries -= 1
                if retries == 0:
                    raise

                _LOGGER.debug("Connect failed, retrying")
                await asyncio.sleep(1.0)

        self.event_channel = transport

        # Ok, so this is not really correct. I believe the shared secret should be used
        # as base for the shared key, but it's hard to get hold of that here
        # (abstractions). It doesn't really matter what the key is (could be hardcoded)
        # as it's merely a security feature. For the sake of it, derive a key from event
        # parameters, it won't hurt (and the key will be different every time).
        out_key, _ = verifier.encryption_keys(
            EVENTS_SALT, EVENTS_WRITE_INFO, EVENTS_READ_INFO
        )
        shared_secret = out_key[0:32]

        setup_resp = await self.rtsp.setup(
            body={
                "streams": [
                    {
                        "audioFormat": 0x800,
                        "audioMode": "default",
                        "controlPort": control_client_port,
                        "ct": 1,  # Raw PCM
                        "isMedia": True,
                        "latencyMax": 88200,
                        "latencyMin": 11025,
                        "shk": shared_secret,
                        "spf": 352,  # Samples Per Frame
                        "sr": 44100,  # Sample rate
                        "type": 0x60,
                        "supportsDynamicStreamID": False,
                        "streamConnectionID": self.rtsp.session_id,
                    }
                ]
            }
        )
        resp = decode_bplist_from_body(setup_resp)
        _LOGGER.debug("Setup stream response: %s", resp)

        stream = resp["streams"][0]

        self.context.control_port = stream["controlPort"]
        self.context.server_port = stream["dataPort"]

        self._cipher = Chacha20Cipher(shared_secret, shared_secret)

    def teardown(self) -> None:
        """Teardown resources allocated by setup efter streaming finished."""
        if self._feedback_task:
            self._feedback_task.cancel()
            self._feedback_task = None
        if self.event_channel:
            self.event_channel.close()
            self.event_channel = None

    async def start_feedback(self) -> None:
        """Start to send feedback (if supported and required)."""
        if self._feedback_task is None:
            self._feedback_task = asyncio.create_task(self._feedback_task_loop())

    async def _feedback_task_loop(self) -> None:
        _LOGGER.debug("Starting feedback task")
        # TODO: Better end condition here to not risk infinite runs?
        while True:
            try:
                await self.rtsp.feedback()
            except Exception:
                _LOGGER.exception("feedback failed")
            await asyncio.sleep(FEEDBACK_INTERVAL)

    async def send_audio_packet(
        self, transport: asyncio.DatagramTransport, rtp_header: bytes, audio: bytes
    ) -> Tuple[int, bytes]:
        """Send audio packet to receiver."""
        # TODO: This part is extremely sub-optimized. Should at least use a memoryview
        # and do in-place operations to avoid copying memory left and right.
        if self._cipher:
            nonce = self._cipher.out_nonce
            aad = rtp_header[4:12]
            audio = self._cipher.encrypt(audio, nonce=nonce, aad=aad)

        packet = rtp_header + audio + nonce

        transport.sendto(packet)

        return self.context.rtpseq, packet
