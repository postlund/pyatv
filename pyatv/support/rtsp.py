"""Implementation of the RTSP protocol.

This is a simple implementation of the RTSP protocol used by Apple (with its quirks
and all). It is somewhat generalized to support both AirPlay 1 and 2.
"""
import asyncio
from hashlib import md5
import logging
import plistlib
from random import randrange
from typing import Any, Dict, Mapping, NamedTuple, Optional, Tuple, Union

from pyatv.protocols.dmap import tags
from pyatv.support.http import HttpConnection, HttpResponse
from pyatv.support.metadata import AudioMetadata

_LOGGER = logging.getLogger(__name__)

FRAMES_PER_PACKET = 352
USER_AGENT = "AirPlay/540.31"

ANNOUNCE_PAYLOAD = (
    "v=0\r\n"
    + "o=iTunes {session_id} 0 IN IP4 {local_ip}\r\n"
    + "s=iTunes\r\n"
    + "c=IN IP4 {remote_ip}\r\n"
    + "t=0 0\r\n"
    + "m=audio 0 RTP/AVP 96\r\n"
    + "a=rtpmap:96 AppleLossless\r\n"
    + f"a=fmtp:96 {FRAMES_PER_PACKET} 0 "
    + "{bits_per_channel} 40 10 14 {channels} 255 0 0 {sample_rate}\r\n"
)

# Used to signal that traffic is to be unencrypted
AUTH_SETUP_UNENCRYPTED = b"\x01"

# Just a static Curve25519 public key used to satisfy the auth-setup step for devices
# requiring that (e.g. AirPort Express). We never verify anything. Source:
# https://github.com/owntone/owntone-server/blob/
# c1db4d914f5cd8e7dbe6c1b6478d68a4c14824af/src/outputs/raop.c#L276
CURVE25519_PUB_KEY = (
    b"\x59\x02\xed\xe9\x0d\x4e\xf2\xbd"
    b"\x4c\xb6\x8a\x63\x30\x03\x82\x07"
    b"\xa9\x4d\xbd\x50\xd8\xaa\x46\x5b"
    b"\x5d\x8c\x01\x2a\x0c\x7e\x1d\x4e"
)


class DigestInfo(NamedTuple):
    """
    OAuth information used for password protected devices.
    """

    username: str
    realm: str
    password: str
    nonce: str


def get_digest_payload(method, uri, user, realm, pwd, nonce):
    """Return the Authorization payload for Apples OAuth."""
    payload = (
        'Digest username="{0}", realm="{1}", nonce="{2}", uri="{3}", response="{4}"'
    )
    ha1 = md5(f"{user}:{realm}:{pwd}".encode("utf-8")).hexdigest()
    ha2 = md5(f"{method}:{uri}".encode("utf-8")).hexdigest()
    di_response = md5(f"{ha1}:{nonce}:{ha2}".encode("utf-8")).hexdigest()
    return payload.format(user, realm, nonce, uri, di_response)


class RtspSession:
    """Representation of an RTSP session."""

    def __init__(self, connection: HttpConnection) -> None:
        """Initialize a new RtspSession."""
        super().__init__()
        self.connection = connection
        self.requests: Dict[int, Tuple[asyncio.Event, Optional[HttpResponse]]] = {}

        self.digest_info: Optional[DigestInfo] = None  # Password authentication
        self.cseq = 0
        self.session_id: int = randrange(2 ** 32)
        self.dacp_id: str = f"{randrange(2 ** 64):X}"
        self.active_remote: int = randrange(2 ** 32)

    @property
    def uri(self) -> str:
        """Return URI used for session requests."""
        return f"rtsp://{self.connection.local_ip}/{self.session_id}"

    @staticmethod
    def error_received(exc) -> None:
        """Handle a connection error."""
        _LOGGER.error("Error received: %s", exc)

    async def info(self) -> Dict[str, object]:
        """Return device information."""
        device_info = await self.exchange("GET", "/info", allow_error=True)

        # If not supported, just return an empty dict
        if device_info.code != 200:
            _LOGGER.debug("Device does not support /info")
            return {}

        body = (
            device_info.body
            if isinstance(device_info.body, bytes)
            else device_info.body.encode("utf-8")
        )
        return plistlib.loads(body)

    async def auth_setup(self) -> HttpResponse:
        """Send auth-setup message."""
        # Payload to say that we want to proceed unencrypted
        body = AUTH_SETUP_UNENCRYPTED + CURVE25519_PUB_KEY

        return await self.exchange(
            "POST",
            "/auth-setup",
            content_type="application/octet-stream",
            body=body,
        )

    # This method is only used by AirPlay 1 and is very specific (e.g. does not support
    # annnouncing arbitrary audio formats) and should probably move to the AirPlay 1
    # specific RAOP implementation. It will however live here for now until something
    # motivates that.
    async def announce(
        self,
        bytes_per_channel: int,
        channels: int,
        sample_rate: int,
        password: Optional[str],
    ) -> HttpResponse:
        """Send ANNOUNCE message."""
        body = ANNOUNCE_PAYLOAD.format(
            session_id=self.session_id,
            local_ip=self.connection.local_ip,
            remote_ip=self.connection.remote_ip,
            bits_per_channel=8 * bytes_per_channel,
            channels=channels,
            sample_rate=sample_rate,
        )

        requires_password: bool = password is not None

        response = await self.exchange(
            "ANNOUNCE",
            content_type="application/sdp",
            body=body,
            allow_error=requires_password,
        )

        # Save the necessary data for password authentication
        www_authenticate = response.headers.get("www-authenticate", None)
        if response.code == 401 and www_authenticate and requires_password:
            _, realm, _, nonce, _ = www_authenticate.split('"')
            info = DigestInfo("pyatv", realm, password, nonce)  # type: ignore
            self.digest_info = info

            response = await self.exchange(
                "ANNOUNCE",
                content_type="application/sdp",
                body=body,
            )

        return response

    async def setup(
        self,
        headers: Optional[Dict[str, Any]] = None,
        body: Optional[Union[str, bytes]] = None,
    ) -> HttpResponse:
        """Send SETUP message."""
        return await self.exchange("SETUP", headers=headers, body=body)

    async def record(
        self,
        headers: Optional[Dict[str, Any]] = None,
        body: Optional[Union[str, bytes]] = None,
    ) -> HttpResponse:
        """Send RECORD message."""
        return await self.exchange("RECORD", headers=headers, body=body)

    async def set_parameter(self, parameter: str, value: str) -> HttpResponse:
        """Send SET_PARAMETER message."""
        return await self.exchange(
            "SET_PARAMETER",
            content_type="text/parameters",
            body=f"{parameter}: {value}",
        )

    async def set_metadata(
        self,
        rtsp_session: int,
        rtpseq: int,
        rtptime: int,
        metadata: AudioMetadata,
    ) -> HttpResponse:
        """Change metadata for what is playing."""
        payload = b""
        if metadata.title:
            payload += tags.string_tag("minm", metadata.title)
        if metadata.album:
            payload += tags.string_tag("asal", metadata.album)
        if metadata.artist:
            payload += tags.string_tag("asar", metadata.artist)

        return await self.exchange(
            "SET_PARAMETER",
            content_type="application/x-dmap-tagged",
            headers={
                "Session": rtsp_session,
                "RTP-Info": f"seq={rtpseq};rtptime={rtptime}",
            },
            body=tags.container_tag("mlit", payload),
        )

    async def feedback(self, allow_error=False) -> HttpResponse:
        """Send SET_PARAMETER message."""
        return await self.exchange("POST", uri="/feedback", allow_error=allow_error)

    async def teardown(self, rtsp_session) -> HttpResponse:
        """Send TEARDOWN message."""
        return await self.exchange("TEARDOWN", headers={"Session": rtsp_session})

    async def exchange(
        self,
        method: str,
        uri: Optional[str] = None,
        content_type: Optional[str] = None,
        headers: Mapping[str, object] = None,
        body: Union[str, bytes] = None,
        allow_error: bool = False,
    ) -> HttpResponse:
        """Send a RTSP message and return response."""
        cseq = self.cseq
        self.cseq += 1

        hdrs = {
            "CSeq": cseq,
            "DACP-ID": self.dacp_id,
            "Active-Remote": self.active_remote,
            "Client-Instance": self.dacp_id,
        }

        # Add the password authentication if required
        if self.digest_info:
            hdrs["Authorization"] = get_digest_payload(
                method, uri or self.uri, *self.digest_info
            )

        if headers:
            hdrs.update(headers)

        # Map an asyncio Event to current CSeq and make the request
        self.requests[cseq] = (asyncio.Event(), None)
        resp = await self.connection.send_and_receive(
            method,
            uri or self.uri,
            protocol="RTSP/1.0",
            user_agent=USER_AGENT,
            content_type=content_type,
            headers=hdrs,
            body=body,
            allow_error=allow_error,
        )

        # The response most likely contains a CSeq and it is also very likely to be
        # the one we expect, but it could be for someone else. So set the correct event
        # and save response.
        resp_cseq = int(resp.headers.get("CSeq", "-1"))
        if resp_cseq in self.requests:
            # Insert response for correct CSeq and activate event
            event, _ = self.requests[resp_cseq]
            self.requests[resp_cseq] = (event, resp)
            event.set()

        # Wait for response to the CSeq we expect
        try:
            await asyncio.wait_for(self.requests[cseq][0].wait(), 4)
            response = self.requests[cseq][1]
        except asyncio.TimeoutError as ex:
            raise TimeoutError(
                f"no response to CSeq {cseq} ({uri or self.uri})"
            ) from ex
        finally:
            del self.requests[cseq]

        # Programming error: forgot to store response before activating event
        if response is None:
            raise RuntimeError(f"no response was saved for {cseq}")

        return response
