"""Play media on a device by sending an URL."""

import asyncio
from contextlib import asynccontextmanager
import logging
import time
import sys

from pyatv import exceptions
from pyatv.protocols.raop.protocols import StreamProtocol, TimingServer
from pyatv.support.rtsp import RtspSession

_LOGGER = logging.getLogger(__name__)

PLAY_RETRIES = 3
WAIT_RETRIES = 5
HEADERS = {
    "User-Agent": "AirPlay/870.14.1",
    "Content-Type": "application/x-apple-binary-plist",
    "X-Apple-ProtocolVersion": "1",
    "X-Apple-StreamID": "1",
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

            # Sometimes AirPlay fails with "Internal Server Error", we
            # apply a "lets try again"-approach to that
            while retry < PLAY_RETRIES:
                _LOGGER.info("Starting to play %s", url)

                try:
                    await self.stream_protocol.play_url(server.port, url, position)
                except Exception as e:
                    retry += 1
                    _LOGGER.warning(
                        "Failed to stream %s, retry %d of %d", url, retry, PLAY_RETRIES
                    )
                    await asyncio.sleep(1.0)
                    continue
                    # TODO: retry only on 500s, raise exception on 400 to 599 and 501 to 600
                    # TODO: is this even needed anymore? If so, need to wrap HTTP codes in an exception from airplayv2.py

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
            state = self.stream_protocol.playbackState()

            _LOGGER.debug(f"Playback-info: {state}")

            if state == "playing":
                video_started = True

            if state == "stopped":
                _LOGGER.info("media has stopped")
                break

            if not video_started and attempts < 0:
                _LOGGER.warning("media failed to start")
                break

            await asyncio.sleep(1)
