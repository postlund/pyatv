"""Play media on a device by sending an URL."""

import asyncio
import logging
import plistlib
from uuid import uuid4

from pyatv import exceptions
from pyatv.support.http import HttpConnection

_LOGGER = logging.getLogger(__name__)

PLAY_RETRIES = 3
WAIT_RETRIES = 5
HEADERS = {
    "User-Agent": "MediaControl/1.0",
    "Content-Type": "application/x-apple-binary-plist",
}


# pylint: disable=too-few-public-methods
class AirPlayPlayer:
    """This class helps with playing media from an URL."""

    def __init__(self, http: HttpConnection) -> None:
        """Initialize a new AirPlay instance."""
        self.http = http

    async def play_url(self, url: str, position: float = 0) -> None:
        """Play media from an URL on the device."""
        body = {
            "Content-Location": url,
            "Start-Position": position,
            "X-Apple-Session-ID": str(uuid4()),
        }

        retry = 0
        while retry < PLAY_RETRIES:
            _LOGGER.debug("Starting to play %s", url)

            # pylint: disable=no-member
            resp = await self.http.post(
                "/play",
                headers=HEADERS,
                body=plistlib.dumps(body, fmt=plistlib.FMT_BINARY),
                allow_error=True,
            )

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
            resp = await self.http.get("/playback-info")
            _LOGGER.debug("Playback-info: %s", resp)

            if resp.body:
                parsed = plistlib.loads(
                    resp.body.encode("utf-8")
                    if isinstance(resp.body, str)
                    else resp.body
                )
            else:
                parsed = {}
                _LOGGER.debug("Got playback-info response without content")

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
