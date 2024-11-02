"""Play media on a device by sending an URL."""

import asyncio
from contextlib import asynccontextmanager
import logging

from pyatv import exceptions
from pyatv.protocols.raop.protocols import StreamProtocol, TimingServer
from pyatv.support.http import decode_bplist_from_body
from pyatv.support.rtsp import RtspSession

_LOGGER = logging.getLogger(__name__)

PLAY_RETRIES = 3
WAIT_RETRIES = 5
HEADERS = {
    "User-Agent": "AirPlay/550.10",
    "Content-Type": "application/x-apple-binary-plist",
    "X-Apple-ProtocolVersion": "1",
    "X-Apple-Stream-ID": "1",
}


@asynccontextmanager
async def timing_server(rtsp: RtspSession):
    """Context manager setting up a timing server."""
    local_addr = (rtsp.connection.local_ip, 0)
    (_, server) = await asyncio.get_event_loop().create_datagram_endpoint(
        TimingServer, local_addr=local_addr
    )
    yield server
    server.close()


# pylint: disable=too-few-public-methods
class AirPlayPlayer:
    """This class helps with playing media from an URL."""

    def __init__(self, rtsp: RtspSession, stream_protocol: StreamProtocol) -> None:
        """Initialize a new AirPlay instance."""
        self.rtsp = rtsp
        self.stream_protocol = stream_protocol

    async def play_url(self, url: str, position: float = 0) -> None:
        """Play media from an URL on the device."""
        retry = 0

        async with timing_server(self.rtsp) as server:
            while retry < PLAY_RETRIES:
                _LOGGER.debug("Starting to play %s", url)

                resp = await self.stream_protocol.play_url(server.port, url, position)

                # Sometimes AirPlay fails with "Internal Server Error", we
                # apply a "lets try again"-approach to that
                if resp.code == 500:
                    retry += 1
                    _LOGGER.debug(
                        "Failed to stream %s, retry %d of %d", url, retry, PLAY_RETRIES
                    )
                    await asyncio.sleep(1.0)
                    continue

                # TODO: Should be more fine-grained
                if 400 <= resp.code < 600:
                    raise exceptions.AuthenticationError(f"status code: {resp.code}")

                await self._wait_for_media_to_end()
                return

        raise exceptions.PlaybackError("Max retries exceeded")

    # Poll playback-info to find out if something is playing. It might take
    # some time until the media starts playing, give it 5 seconds (attempts)
    async def _wait_for_media_to_end(self) -> None:
        attempts: int = WAIT_RETRIES
        video_started: bool = False

        while True:
            # In some cases this call will fail if video was stopped by the sender,
            # e.g. stopping video via remote control. For now, handle this gracefully
            # by not spewing an exception.
            try:
                resp = await self.rtsp.connection.get("/playback-info")
            except (RuntimeError, exceptions.ConnectionLostError):
                _LOGGER.debug("Connection was lost, assuming video playback stopped")
                break

            _LOGGER.debug("Playback-info: %s", resp)

            if resp.body:
                parsed = decode_bplist_from_body(resp)
            else:
                parsed = {}
                _LOGGER.debug("Got playback-info response without content")

            # In case we got an error, abort with that here
            if "error" in parsed:
                code = parsed["error"].get("code", "unknown")
                domain = parsed["error"].get("domain", "unknown domain")
                raise exceptions.PlaybackError(
                    f"got error {code} ({domain}) when playing video"
                )

            # duration is only available if something is playing
            if "duration" in parsed:
                video_started = True
                attempts = -1
            else:
                video_started = False
                if attempts >= 0:
                    attempts -= 1

            if not video_started and attempts < 0:
                _LOGGER.debug("media playback ended")
                break

            await asyncio.sleep(1)
