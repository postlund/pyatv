"""Implementation of AirPlay v2 protocol logic."""

import asyncio
import logging
import plistlib
from typing import Any, Dict, Mapping, Optional, Tuple, cast
from uuid import uuid4

from pyatv import exceptions
from pyatv.auth.hap_channel import setup_channel
from pyatv.auth.hap_pairing import PairVerifyProcedure
from pyatv.protocols.airplay.auth import verify_connection
from pyatv.protocols.airplay.channels import EventChannel, EventChannelListener
from pyatv.protocols.raop.protocols import StreamContext, StreamProtocol
from pyatv.support.chacha20 import Chacha20Cipher, Chacha20Cipher8byteNonce
from pyatv.support.http import HttpResponse, decode_bplist_from_body
from pyatv.support.rtsp import RtspSession

_LOGGER = logging.getLogger(__name__)

EVENTS_SALT = "Events-Salt"
EVENTS_WRITE_INFO = "Events-Write-Encryption-Key"
EVENTS_READ_INFO = "Events-Read-Encryption-Key"

FEEDBACK_INTERVAL = 2.0  # Seconds

HEADERS = {
    "User-Agent": "AirPlay/550.10",
    "Content-Type": "application/x-apple-binary-plist",
    "X-Apple-ProtocolVersion": "1",
    "X-Apple-Session-ID": str(uuid4()).lower(),
    "X-Apple-Stream-ID": "1",
}

# Modern receivers drive video through POST /command rather than POST /play.
COMMAND_HEADERS = {
    "User-Agent": "AirPlay/960.13.1",
    "Content-Type": "application/x-apple-binary-plist",
}

# Identifies the sender as wanting a remote control session (type 130,
# controlType 1). Distinct from the MRP data channel, which uses controlType 2
# and clientTypeUUID 1910A70F-DBC0-4242-AF95-115DB30604E1.
RCS_CLIENT_TYPE_UUID = "A6B27562-B43A-4F2D-B75F-82391E250194"


class AirPlayV2(StreamProtocol, EventChannelListener):
    """Stream protocol used for AirPlay v1 support."""

    def __init__(self, context: StreamContext, rtsp: RtspSession) -> None:
        """Initialize a new AirPlayV2 instance."""
        super().__init__()
        self.context = context
        self.rtsp = rtsp
        self.event_channel: Optional[asyncio.BaseTransport] = None
        self._verifier: Optional[PairVerifyProcedure] = None
        self._cipher: Optional[Chacha20Cipher] = None
        self._feedback_task: Optional[asyncio.Task] = None
        # Set once a remote control session has been registered, which is what
        # makes POST /command available.
        self._rcs_stream_id: Optional[int] = None
        self._item_uuid = str(uuid4()).upper()
        # The receiver reports playback state on the event channel rather than
        # answering GET /playback-info, so end of media is signalled here.
        self._media_ended: asyncio.Event = asyncio.Event()

        self.uuid = str(uuid4())

    async def _setup_base(self, timing_server_port: int) -> None:
        # The video path verifies up front, so do not verify twice on the same
        # connection when falling back to the legacy setup.
        if self._verifier is None:
            self._verifier = await verify_connection(
                self.context.credentials, self.rtsp.connection
            )

        setup_resp = await self.rtsp.setup(
            body={
                "deviceID": "AA:BB:CC:DD:EE:FF",
                "sessionUUID": str(uuid4()).upper(),
                "timingPort": timing_server_port,
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
                    self._verifier,
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

    async def setup(self, timing_server_port: int, control_client_port: int) -> None:
        """To setup connection prior to starting to stream."""
        await self._setup_base(timing_server_port)
        await self.setup_audio_stream(control_client_port)

    async def setup_audio_stream(self, control_client_port: int) -> None:
        """Setup a new stream used for audio."""
        if self._verifier is None:
            raise exceptions.InvalidStateError("base stream not set up")

        # Ok, so this is not really correct. I believe the shared secret should be used
        # as base for the shared key, but it's hard to get hold of that here
        # (abstractions). It doesn't really matter what the key is (could be hardcoded)
        # as it's merely a security feature. For the sake of it, derive a key from event
        # parameters, it won't hurt (and the key will be different every time).
        out_key, _ = self._verifier.encryption_keys(
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

        self._cipher = Chacha20Cipher8byteNonce(shared_secret, shared_secret)

    def teardown(self) -> None:
        """Teardown resources allocated by setup efter streaming finished."""
        self._media_ended.set()
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
            except Exception as ex:
                # Treat feedback as "best effort" and don't raise any errors
                _LOGGER.debug("Feedback failed: %s", ex)
            await asyncio.sleep(FEEDBACK_INTERVAL)

    async def send_audio_packet(
        self, transport: asyncio.DatagramTransport, rtp_header: bytes, audio: bytes
    ) -> Tuple[int, bytes]:
        """Send audio packet to receiver."""
        # TODO: This part is extremely sub-optimized. Should at least use a memoryview
        # and do in-place operations to avoid copying memory left and right.
        nonce = b""
        if self._cipher:
            # Save the nonce that will be used by the next encrypt call as it is
            # included in the audio packet.
            nonce = self._cipher.out_nonce
            aad = rtp_header[4:12]

            # Do _not_ pass nonce=nonce here as that not increase the internal counter
            # of outgoing messages. We would just send zero as nonce. We did that in
            # the past and Apple doesn't seem to care, but other vendors might do.
            audio = self._cipher.encrypt(audio, aad=aad)

        # Build the audio packet. Make sure to drop the "upper four" bytes of the nonce
        # as only eight byte nonces are used for encryption (the Chacha20
        # implementation however returns twelve bytes according to specification).
        packet = rtp_header + audio + nonce[-8:]

        transport.sendto(packet)

        return self.context.rtpseq, packet

    async def _setup_video_session(self) -> None:
        """Set up a session for video playback.

        Video sessions are timed with PTP and carry a peer list, unlike the NTP
        based setup used for audio streaming.

        PTP is required, and not only because a peer list is expected. The NTP
        setup is accepted -- SETUP succeeds, a remote control session can be
        registered, the receiver fetches the media and playback starts -- but the
        session does not survive it. No events arrive on the event channel, so
        there is no playback state, and the picture collapses after roughly
        twenty seconds. Measured on tvOS 26.5: PTP is still playing at 60s with
        26 events over a short session; NTP delivers zero events and is gone by
        27s.
        """
        local_ip = self.rtsp.connection.local_ip
        peer = {
            "ID": self.uuid.upper(),
            "Addresses": [local_ip],
            "DeviceType": 0,
            "SupportsClockPortMatchingOverride": True,
        }

        setup_resp = await self.rtsp.setup(
            body={
                "timingProtocol": "PTP",
                "timingPeerInfo": peer,
                "timingPeerList": [peer],
                "sessionUUID": str(uuid4()).upper(),
                "sessionCorrelationUUID": self.uuid.upper(),
                "updateSessionRequest": False,
                "statsCollectionEnabled": False,
                "isMultiSelectAirPlay": False,
                "deviceID": "AA:BB:CC:DD:EE:FF",
                "macAddress": "AA:BB:CC:DD:EE:FF",
                "model": "iPhone14,3",
                "name": "pyatv",
                "osName": "iPhone OS",
                "osVersion": "16.5",
                "osBuildVersion": "20F66",
                "sourceVersion": "690.7.1",
            }
        )
        resp = decode_bplist_from_body(setup_resp)
        _LOGGER.debug("Video setup response: %s", resp)

        event_port = resp.get("eventPort", 0)
        if event_port:
            transport, protocol = await setup_channel(
                EventChannel,
                self._verifier,
                self.rtsp.connection.remote_ip,
                event_port,
                EVENTS_SALT,
                EVENTS_READ_INFO,
                EVENTS_WRITE_INFO,
            )
            cast(EventChannel, protocol).listener = self
            self.event_channel = transport

    async def _setup_remote_control_session(self) -> bool:
        """Register a remote control session, which is what enables /command.

        Returns True if the receiver accepted it. The receiver answers without a
        dataPort, so nothing is ever connected -- asking for the channel is the
        entire purpose of this request.
        """
        try:
            info = decode_bplist_from_body(await self.rtsp.connection.get("/info"))
            psi = info.get("psi")
        except Exception:  # pylint: disable=broad-except
            _LOGGER.debug("Failed to read /info", exc_info=True)
            return False

        if not psi:
            _LOGGER.debug("Receiver did not report psi, cannot set up RCS")
            return False

        try:
            setup_resp = await self.rtsp.setup(
                body={
                    "streams": [
                        {
                            "type": 130,
                            "controlType": 1,
                            "channelID": f"{psi}-RCS-1",
                            "clientUUID": str(uuid4()).upper(),
                            "clientTypeUUID": RCS_CLIENT_TYPE_UUID,
                        }
                    ]
                }
            )
        except exceptions.HttpError:
            _LOGGER.debug("Receiver rejected remote control session", exc_info=True)
            return False

        resp = decode_bplist_from_body(setup_resp)
        streams = resp.get("streams") or []
        if not streams:
            _LOGGER.debug("No streams in RCS setup response: %s", resp)
            return False

        self._rcs_stream_id = streams[0].get("streamID", 1)
        _LOGGER.debug("Remote control session established (id=%s)", self._rcs_stream_id)
        return True

    async def send_command(self, command: Dict[str, Any]) -> HttpResponse:
        """Send a command to the receiver via POST /command.

        The body is a plist whose "data" member is itself a serialized plist.
        """
        headers = dict(COMMAND_HEADERS)
        headers["X-Apple-StreamID"] = str(self._rcs_stream_id or 1)
        inner = plistlib.dumps(command, fmt=plistlib.FMT_BINARY)
        return await self.rtsp.connection.post(
            "/command",
            headers=headers,
            body=plistlib.dumps({"params": {"data": inner}}, fmt=plistlib.FMT_BINARY),
            allow_error=True,
        )

    def handle_event(self, event: Mapping[str, Any]) -> None:
        """Handle an event pushed by the receiver on the event channel."""
        kind = event.get("type")
        if kind == "playbackState":
            state = event.get("name")
            _LOGGER.debug("Playback state: %s", state)
            # A replacement goes playing -> loading -> playing, so "stopped" is
            # only reported when nothing is playing any more.
            if state == "stopped":
                self._media_ended.set()
        elif kind == "notification":
            _LOGGER.debug("Playback notification: %s", event.get("name"))

    async def wait_for_media_end(self) -> bool:
        """Wait until the receiver reports that playback finished."""
        if self._rcs_stream_id is None:
            return False

        await self._media_ended.wait()
        return True

    async def play_url(self, timing_server_port: int, url: str, position: float = 0.0):
        """Play media from a URL.

        Modern receivers drive video through a play queue over POST /command,
        which only becomes available once a remote control session is
        registered. Receivers that do not offer one still get POST /play.
        """
        # The order below mirrors what a real sender does. It matters: reading
        # /info before pair-verify, or starting feedback before RECORD, makes the
        # receiver drop the connection part way through the play queue commands.
        self._verifier = await verify_connection(
            self.context.credentials, self.rtsp.connection
        )

        try:
            await self._setup_video_session()
        except exceptions.HttpError as ex:
            # Receivers that predate PTP timed video sessions reject this setup.
            # Fall back to the audio style setup, which is what /play expects.
            _LOGGER.debug("Video session setup rejected (%s), using legacy setup", ex)
            await self._setup_base(timing_server_port)
            await self.start_feedback()
            await self.rtsp.record()
            return await self._play_url_legacy(url, position)

        await self.rtsp.record()
        use_command = await self._setup_remote_control_session()

        # Feedback must not start until the play commands have been issued.
        # It shares this connection, and an RTSP feedback request in flight
        # alongside an HTTP /command request makes the receiver drop the
        # connection part way through the play queue.
        if use_command:
            resp = await self._play_url_command(url, position)
            await self.start_feedback()
            return resp

        _LOGGER.debug("No remote control session, falling back to POST /play")
        resp = await self._play_url_legacy(url, position)
        await self.start_feedback()
        return resp

    def _queue_item(self, url: str, position: float) -> Dict[str, Any]:
        """Build a play queue item for the current item uuid."""
        return {
            "uuid": self._item_uuid,
            "Content-Location": url,
            "mediaType": "file",
            "IsTLSEnabled": url.startswith("https://"),
            "playbackRestrictions": 0,
            "referenceRestrictions": 2,
            "supportsIntegratedTimeline": False,
            "snapTimeToPausePlayback": False,
            "clientBundleID": "dev.pyatv",
            "clientProcName": "pyatv",
            # playerLoggingID must be at most 6 characters. A longer value makes
            # the receiver close the connection part way through the play queue
            # commands, with no error response. playerItemLoggingID is not
            # subject to the same limit.
            "playerLoggingID": "P/ATV",
            "playerItemLoggingID": "I/PYATV.01",
            "Start-Position": {
                "flags": 1,
                "value": int(position),
                "epoch": 0,
                "timescale": 1,
            },
        }

    async def _play_url_command(self, url: str, position: float) -> HttpResponse:
        """Start playback using the play queue protocol."""
        resp = await self.send_command(
            {"type": "insertPlayQueueItem", "item": self._queue_item(url, position)}
        )
        if resp.code != 200:
            return resp

        await self.send_command(
            {
                "type": "setProperty",
                "property": "isInterestedInDateRange",
                "value": True,
                "item": {"uuid": self._item_uuid},
            }
        )
        # Playback starts paused without this.
        await self.send_command({"type": "setRate", "rate": 1.0})
        return resp

    async def _play_url_legacy(self, url: str, position: float) -> HttpResponse:
        """Start playback using POST /play, for receivers without /command."""
        # Most fields are not needed here, but keeping them for reference
        body = {
            "Content-Location": url,
            "Start-Position-Seconds": position,
            "uuid": self.uuid,
            "streamType": 1,
            "mediaType": "file",
            "mightSupportStorePastisKeyRequests": True,
            "playbackRestrictions": 0,
            "secureConnectionMs": 22,
            "volume": 1.0,
            "infoMs": 122,
            "connectMs": 18,
            "authMs": 0,
            "bonjourMs": 0,
            "referenceRestrictions": 3,
            "SenderMACAddress": "AA:BB:CC:DD:EE:FF",
            "model": "iPhone14,3",
            "postAuthMs": 0,
            "clientBundleID": "dev.pyatv.GPU",
            "clientProcName": "dev.pyatv.GPU",
            "osBuildVersion": "20G1116",
            "rate": 1.0,
        }

        # Actually start the stream
        resp = await self.rtsp.connection.post(
            "/play",
            headers=HEADERS,
            body=plistlib.dumps(
                body, fmt=plistlib.FMT_BINARY  # pylint: disable=no-member
            ),
            allow_error=True,
        )

        # Various commands, most of which are probably not needed for pyatv. Doing them
        # anyways, just to be sure things work. Most important command is "/rate" as
        # that sets playback rate to 100% (will start paused otherwise).
        # TODO: Maybe check some return values?
        await self.rtsp.exchange(
            "PUT", uri="/setProperty?isInterestedInDateRange", body={"value": True}
        )
        await self.rtsp.exchange(
            "PUT", uri="/setProperty?actionAtItemEnd", body={"value": 0}
        )
        await self.rtsp.exchange("POST", uri="/rate?value=1.000000")
        await self.rtsp.exchange(
            "PUT",
            uri="/setProperty?forwardEndTime",
            body={"value": {"flags": 0, "value": 0, "epoch": 0, "timescale": 0}},
        )
        await self.rtsp.exchange(
            "PUT",
            uri="/setProperty?reverseEndTime",
            body={"value": {"flags": 0, "value": 0, "epoch": 0, "timescale": 0}},
        )

        return resp
