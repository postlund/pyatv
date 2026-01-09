"""Implementation of AirPlay v2 protocol logic."""

import asyncio
import logging
import plistlib
from typing import Optional, Tuple, Dict
from uuid import uuid4

from pyatv import exceptions
from pyatv.auth.hap_channel import setup_channel
from pyatv.auth.hap_pairing import PairVerifyProcedure
from pyatv.protocols.airplay.auth import verify_connection
from pyatv.protocols.airplay.channels import EventChannel
from pyatv.protocols.raop.protocols import StreamContext, StreamProtocol
from pyatv.support.chacha20 import Chacha20Cipher, Chacha20Cipher8byteNonce
from pyatv.support.http import decode_plist_body
from pyatv.support.rtsp import RtspSession

_LOGGER = logging.getLogger(__name__)

EVENTS_SALT = "Events-Salt"
EVENTS_WRITE_INFO = "Events-Write-Encryption-Key"
EVENTS_READ_INFO = "Events-Read-Encryption-Key"

FEEDBACK_INTERVAL = 2.0  # Seconds

SESSION_ID = str(uuid4()).upper()

HEADERS = {
    "User-Agent": "AirPlay/870.14.1",
    "Content-Type": "application/x-apple-binary-plist",
    "X-Apple-ProtocolVersion": "1",
    "X-Apple-Session-ID": SESSION_ID,
    "X-Apple-StreamID": "1",
    "CSeq": "1"
}

class AirPlayV2(StreamProtocol):
    """Stream protocol used for AirPlay v2 support."""

    def __init__(self, context: StreamContext, rtsp: RtspSession) -> None:
        """Initialize a new AirPlayV2 instance."""
        super().__init__()
        self.context = context
        self.rtsp = rtsp
        self.event_transport: Optional[asyncio.BaseTransport] = None
        self._verifier: Optional[PairVerifyProcedure] = None
        self._cipher: Optional[Chacha20Cipher] = None
        self._feedback_task: Optional[asyncio.Task] = None
        self._messageID = 1
        self._playbackState = None
        self.uuid = str(uuid4())

    def _playbackStateListener(self, info):
        self._playbackState = info

    async def _setup_base(self, timing_server_port: int) -> None:
        self._verifier = await verify_connection(
            self.context.credentials, self.rtsp.connection
        )

        setup_resp = await self.rtsp.setup(
            body={
                "deviceID": "AA:BB:CC:DD:EE:FF",
                "sessionUUID": SESSION_ID,
                "sessionCorrelationUUID": str(uuid4()).upper(),
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
        resp = decode_plist_body(setup_resp.body)

        event_port = resp.get("eventPort", 0)

        # This is a bit hacky, but I noticed that airplay2-receiver seems to set up the
        # event channel some time after responding with the port used for it. So the
        # connect call fails. By doing some retries here, it will work after some
        # attempts. So keeping that here for compatibility reason.
        retries = 5
        transport = None
        while transport is None:
            try:
                transport, channel = await setup_channel(
                    EventChannel,
                    self._verifier,
                    self.rtsp.connection.remote_ip,
                    event_port,
                    EVENTS_SALT,
                    EVENTS_READ_INFO,
                    EVENTS_WRITE_INFO,
                )
            except (ConnectionRefusedError, OSError):
                retries -= 1
                if retries == 0:
                    raise

                _LOGGER.warning("Connect failed, retrying")
                await asyncio.sleep(1.0)

        self.event_transport = transport
        self.event_channel = channel
        self.event_channel.listener(self._playbackStateListener)

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
        resp = decode_plist_body(setup_resp.body)
        _LOGGER.debug("Setup stream response: %s", resp)

        stream = resp["streams"][0]

        self.context.control_port = stream["controlPort"]
        self.context.server_port = stream["dataPort"]

        self._cipher = Chacha20Cipher8byteNonce(shared_secret, shared_secret)

    def teardown(self) -> None:
        """Teardown resources allocated by setup efter streaming finished."""
        if self._feedback_task:
            self._feedback_task.cancel()
            self._feedback_task = None
        if self.event_transport:
            self.event_transport.close()
            self.event_transport = None

    async def start_feedback(self) -> None:
        """Start to send feedback (if supported and required)."""
        if self._feedback_task is None:
            self._feedback_task = asyncio.create_task(self._feedback_task_loop())

    async def _feedback_task_loop(self) -> None:
        _LOGGER.debug("Starting feedback task")
        # TODO: Better end condition here to not risk infinite runs?
        while True:
            await asyncio.sleep(FEEDBACK_INTERVAL)
            try:
                await self.rtsp.feedback()
            except Exception as ex:
                # Treat feedback as "best effort" and don't raise any errors
                _LOGGER.debug("Feedback failed: %s", ex)

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

    async def send_command(self, data):
        # Most fields are not needed here, but keeping them for reference
        body = {
            "params": {
                "data": plistlib.dumps(data, fmt=plistlib.FMT_BINARY, sort_keys=False)
            }
        }

        # Send the command
        return await self.rtsp.connection.post(
            "/command",
            headers=HEADERS,
            body=plistlib.dumps(
                body, fmt=plistlib.FMT_BINARY  # pylint: disable=no-member
            ),
            allow_error=True,
        )        

    async def setup_url_stream(self) -> dict: 
        """Setup a new stream used for video over http."""
        if self._verifier is None:
            raise exceptions.InvalidStateError("base stream not set up")

        setup_resp = await self.rtsp.setup(
            body={
                    "streams": [
                        {
                            'clientUUID': '2E0A9FBA-182D-4E04-8A5D-EC018BD8C408',
                            'clientTypeUUID': 'A6B27562-B43A-4F2D-B75F-82391E250194',
                            'channelID': '36:CB:3F:E1:93:B0-RCS-1',
                            'controlType': 1,
                            'type': 130
                        }
                    ]
            })
        
        resp = decode_plist_body(setup_resp.body)
        HEADERS["X-Apple-StreamID"] = resp["streams"][0]["streamID"]
        return resp

    async def play_url(self, timing_server_port: int, url: str, position: float = 0.0) -> int :
        """Play media from a URL."""        
        if not self._verifier:
            await self._setup_base(timing_server_port)
            await self.start_feedback()
            
        await self.rtsp.info()
        await self.rtsp.record()
        resp = await self.setup_url_stream()

        item = {
            "uuid": "30BFEC7B-E49B-47E9-8839-E009D7F9CD7F"
        }

        resp = await self.send_command({
            "type": "insertPlayQueueItem",
            "item": {
                "uuid": item["uuid"],
                "mediaType": "file",
                "Content-Location": url,
            }
        })

        await self.send_command({
            "type": "setProperty",
            "value": True,
            "property": "isInterestedInDateRange",
            "item": item
        })

        await self.send_command({
            "type": "setProperty",
            "value": 1,
            "property": "actionAtItemEnd"
        })

        await self.send_command({
            "type": "setRate",
            "rate": 1.0,
        })

        return self._playbackState

    async def playbackInfo(self) -> Dict:
        id = self._messageID
        self._messageID += 1
        await self.send_command({'type': 'playbackInfo', 'kind': 'request', 'messageID': id})
        response = await self.event_channel.responseFor(id)
        return response
    
    def playbackState(self) -> Dict:
        if self._playbackState:
            if 'params' in self._playbackState:
                return self._playbackState['params']['playbackState']
            else:
                return self._playbackState['name']
        else:
            return None
