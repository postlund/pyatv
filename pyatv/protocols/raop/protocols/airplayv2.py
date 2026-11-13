"""Implementation of AirPlay v2 protocol logic."""

import asyncio
import logging
import plistlib
from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    List,
    Mapping,
    Optional,
    Set,
    Tuple,
    cast,
)
from uuid import uuid4

import aiohttp

from pyatv import exceptions
from pyatv.auth.hap_channel import setup_channel
from pyatv.auth.hap_pairing import PairVerifyProcedure
from pyatv.protocols.airplay.auth import verify_connection
from pyatv.protocols.airplay.channels import EventChannel
from pyatv.protocols.raop.protocols import StreamContext, StreamProtocol
from pyatv.support.chacha20 import Chacha20Cipher, Chacha20Cipher8byteNonce
from pyatv.support.http import HttpResponse, decode_bplist_from_body
from pyatv.support.rtsp import HTTP_PROTOCOL, RtspSession

_LOGGER = logging.getLogger(__name__)

EVENTS_SALT = "Events-Salt"
EVENTS_WRITE_INFO = "Events-Write-Encryption-Key"
EVENTS_READ_INFO = "Events-Read-Encryption-Key"

FEEDBACK_INTERVAL = 2.0  # Seconds

COMMAND_USER_AGENT = "AirPlay/870.14.1"
REMOTE_CONTROL_CLIENT_TYPE = "A6B27562-B43A-4F2D-B75F-82391E250194"

# A receiver that cannot load a URL itself (e.g. the server refuses it) sends an
# "unhandledURL" request (FCUP) and lets the sender fetch it. This is meant for
# playlists and content keys, so responses are kept in memory and capped.
FCUP_MAX_RESPONSE_SIZE = 8 * 1024 * 1024
FCUP_FETCH_TIMEOUT = 20.0  # Seconds
FCUP_FETCH_FAILED = 502
_FCUP_SKIPPED_REQUEST_HEADERS = {"accept-encoding", "host"}
_FCUP_SKIPPED_RESPONSE_HEADERS = {
    "connection",
    "content-encoding",
    "content-length",
    "keep-alive",
    "transfer-encoding",
}

# (status code, response headers, response body)
UrlFetchResult = Tuple[int, Dict[str, str], bytes]
UrlFetcher = Callable[[str, Mapping[str, str]], Awaitable[UrlFetchResult]]


async def fetch_unhandled_url(url: str, headers: Mapping[str, str]) -> UrlFetchResult:
    """Fetch a URL on behalf of the receiver.

    The body is decoded (no content encoding) and headers that no longer apply to
    the decoded body are left out.
    """
    timeout = aiohttp.ClientTimeout(total=FCUP_FETCH_TIMEOUT)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(url, headers=dict(headers)) as resp:
            if (
                resp.content_length is not None
                and resp.content_length > FCUP_MAX_RESPONSE_SIZE
            ):
                raise exceptions.ProtocolError(
                    f"response too large ({resp.content_length} bytes)"
                )
            data = bytearray()
            async for chunk in resp.content.iter_chunked(64 * 1024):
                data += chunk
                if len(data) > FCUP_MAX_RESPONSE_SIZE:
                    raise exceptions.ProtocolError(
                        f"response larger than {FCUP_MAX_RESPONSE_SIZE} bytes"
                    )
            response_headers = {
                key: value
                for key, value in resp.headers.items()
                if key.lower() not in _FCUP_SKIPPED_RESPONSE_HEADERS
            }
            response_headers["Content-Length"] = str(len(data))
            return resp.status, response_headers, bytes(data)


class AirPlayV2(StreamProtocol):
    """Stream protocol used for AirPlay v2 support."""

    def __init__(self, context: StreamContext, rtsp: RtspSession) -> None:
        """Initialize a new AirPlayV2 instance."""
        super().__init__()
        self.context = context
        self.rtsp = rtsp
        self.event_transport: Optional[asyncio.BaseTransport] = None
        self.event_channel: Optional[EventChannel] = None
        self._verifier: Optional[PairVerifyProcedure] = None
        self._cipher: Optional[Chacha20Cipher] = None
        self._feedback_task: Optional[asyncio.Task] = None
        self._playback_state: Optional[str] = None
        self._playback_state_changed = asyncio.Event()
        self._session_id = str(uuid4()).upper()
        sender_bytes = bytearray(uuid4().bytes[:6])
        sender_bytes[0] = (sender_bytes[0] & 0xFC) | 0x02
        self._sender_device_id = ":".join(f"{byte:02X}" for byte in sender_bytes)
        self._stream_id: Optional[int] = None
        self.url_fetcher: UrlFetcher = fetch_unhandled_url
        self._fcup_tasks: Set[asyncio.Task] = set()
        self._url_load_error: Optional[str] = None

    async def _setup_base(self, timing_server_port: int) -> None:
        self._verifier = await verify_connection(
            self.context.credentials, self.rtsp.connection
        )

        setup_resp = await self.rtsp.setup(
            body={
                "deviceID": self._sender_device_id,
                "sessionUUID": self._session_id,
                "sessionCorrelationUUID": str(uuid4()).upper(),
                "timingPort": timing_server_port,
                "timingProtocol": "NTP",
                "isMultiSelectAirPlay": True,
                "groupContainsGroupLeader": False,
                "macAddress": self._sender_device_id,
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
                transport, protocol = await setup_channel(
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

                _LOGGER.debug("Connect failed, retrying")
                await asyncio.sleep(1.0)

        self.event_transport = transport
        self.event_channel = cast(EventChannel, protocol)
        self.event_channel.set_event_listener(self._handle_event)

    def _handle_event(self, event: Dict[str, Any]) -> None:
        if event.get("type") == "unhandledURL" and event.get("kind") == "request":
            task = asyncio.ensure_future(self._answer_unhandled_url(event))
            self._fcup_tasks.add(task)
            task.add_done_callback(self._fcup_tasks.discard)
            return

        if event.get("type") != "playbackState":
            return

        params = event.get("params")
        state = params.get("playbackState") if isinstance(params, dict) else None
        if state is None:
            state = event.get("name")
        if isinstance(state, str):
            normalized_state = state.lower()
            if normalized_state != self._playback_state:
                self._playback_state = normalized_state
                self._playback_state_changed.set()

    async def _answer_unhandled_url(self, event: Dict[str, Any]) -> None:
        """Fetch a URL the receiver could not load and send the result back."""
        request = event.get("request")
        message_id = event.get("messageID")
        url = request.get("FCUP_Response_URL") if isinstance(request, dict) else None
        if not isinstance(url, str) or message_id is None:
            _LOGGER.warning("Ignoring malformed unhandledURL request: %s", event)
            return
        assert isinstance(request, dict)

        request_headers = request.get("FCUP_Response_Headers")
        headers = {
            str(key): str(value)
            for key, value in (
                request_headers.items() if isinstance(request_headers, dict) else []
            )
            if str(key).lower() not in _FCUP_SKIPPED_REQUEST_HEADERS
        }

        _LOGGER.debug("Receiver asked sender to fetch %s", url)
        try:
            status, response_headers, data = await self.url_fetcher(url, headers)
        except (
            aiohttp.ClientError,
            asyncio.TimeoutError,
            exceptions.ProtocolError,
        ) as ex:
            _LOGGER.warning("Failed to fetch %s for receiver", url, exc_info=True)
            status, response_headers, data = FCUP_FETCH_FAILED, {}, b""
            self._set_url_load_error(f"{url} could not be fetched: {ex!r}")
        else:
            _LOGGER.debug(
                "Fetched %s for receiver: %d (%d bytes)", url, status, len(data)
            )
            if not 200 <= status < 300:
                self._set_url_load_error(f"{url} returned HTTP {status}")
            elif not request.get("FCUP_Response_IsContentKeyRequest") and not (
                data.lstrip().startswith(b"#EXTM3U")
            ):
                # Seen on tvOS 27: a plain media file passed this way never plays
                _LOGGER.warning(
                    "Receiver could not load %s itself and it is not an HLS "
                    "playlist; playback will probably not start",
                    url,
                )

        reply = {
            "kind": "response",
            "messageID": message_id,
            "type": "unhandledURL",
            "response": {
                "FCUP_Response_URL": url,
                "FCUP_Response_RequestID": request.get("FCUP_Response_RequestID", 0),
                "FCUP_Response_StatusCode": status,
                "FCUP_Response_Headers": response_headers,
                "FCUP_Response_Data": data,
            },
        }
        try:
            response = await self._send_url_command(reply)
        except Exception:  # pylint: disable=broad-except
            # Runs as a detached task, so nobody else would see the error
            _LOGGER.exception("Failed to answer unhandledURL request for %s", url)
            return
        if not 200 <= response.code < 300:
            _LOGGER.warning(
                "Receiver rejected unhandledURL response: %d", response.code
            )

    def _set_url_load_error(self, error: str) -> None:
        self._url_load_error = error
        self._playback_state_changed.set()

    @property
    def url_load_error(self) -> Optional[str]:
        """Return why the receiver could not load the media URL, if known."""
        return self._url_load_error

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
        if self._feedback_task:
            self._feedback_task.cancel()
            self._feedback_task = None
        for task in self._fcup_tasks:
            task.cancel()
        self._fcup_tasks.clear()
        if self.event_transport:
            self.event_transport.close()
            self.event_transport = None
        if self.event_channel:
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

    async def _setup_url_stream(self) -> None:
        response = await self.rtsp.setup(
            body={
                "streams": [
                    {
                        "clientUUID": str(uuid4()).upper(),
                        "clientTypeUUID": REMOTE_CONTROL_CLIENT_TYPE,
                        "channelID": f"{self._sender_device_id}-RCS-1",
                        "controlType": 1,
                        "type": 130,
                    }
                ]
            }
        )
        payload = decode_bplist_from_body(response)
        streams = payload.get("streams", [])
        if not streams or "streamID" not in streams[0]:
            raise exceptions.ProtocolError(
                "missing URL control stream in SETUP response"
            )
        self._stream_id = int(streams[0]["streamID"])

    async def _send_url_command(self, command: Dict[str, Any]) -> HttpResponse:
        if self._stream_id is None:
            raise exceptions.InvalidStateError("URL control stream not set up")

        body = {
            "params": {
                "data": plistlib.dumps(
                    command,
                    fmt=plistlib.FMT_BINARY,  # pylint: disable=no-member
                    sort_keys=False,
                )
            }
        }
        return await self.rtsp.exchange(
            "POST",
            uri="/command",
            protocol=HTTP_PROTOCOL,
            headers={
                "User-Agent": COMMAND_USER_AGENT,
                "X-Apple-ProtocolVersion": "1",
                "X-Apple-Session-ID": self._session_id,
                "X-Apple-StreamID": self._stream_id,
            },
            body=body,
            allow_error=True,
        )

    async def play_url(
        self, timing_server_port: int, url: str, position: float = 0.0
    ) -> HttpResponse:
        """Play media from a URL."""
        if self._verifier is None:
            await self._setup_base(timing_server_port)
            await self.start_feedback()
        await self.rtsp.info()
        await self.rtsp.record()
        await self._setup_url_stream()
        self._url_load_error = None

        item = {
            "uuid": str(uuid4()).upper(),
            "mediaType": "file",
            "Content-Location": url,
            "Start-Position-Seconds": position,
        }
        commands: List[Dict[str, Any]] = [
            {"type": "insertPlayQueueItem", "item": item},
            {
                "type": "setProperty",
                "value": True,
                "property": "isInterestedInDateRange",
                "item": {"uuid": item["uuid"]},
            },
            {"type": "setProperty", "value": 1, "property": "actionAtItemEnd"},
            {"type": "setRate", "rate": 1.0},
        ]

        response: Optional[HttpResponse] = None
        for command in commands:
            response = await self._send_url_command(command)
            if not 200 <= response.code < 300:
                return response

        assert response is not None
        return response

    @property
    def playback_state(self) -> Optional[str]:
        """Return the latest playback state from the event channel."""
        return self._playback_state

    async def wait_for_playback_state_change(
        self, previous_state: Optional[str], timeout: float
    ) -> Optional[str]:
        """Wait for the event channel to report a new playback state."""
        self._playback_state_changed.clear()
        if self._playback_state != previous_state:
            return self._playback_state
        try:
            await asyncio.wait_for(self._playback_state_changed.wait(), timeout)
        except asyncio.TimeoutError:
            pass
        return self._playback_state

    @property
    def supports_playback_state(self) -> bool:
        """Return whether playback state is reported by this stream."""
        return True
