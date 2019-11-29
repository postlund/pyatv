"""Play media on a device by sending an URL."""

import logging
import asyncio
import plistlib
from uuid import uuid4

from pyatv import exceptions


_LOGGER = logging.getLogger(__name__)

TIMEOUT = 10
HEADERS = {
    'User-Agent': 'MediaControl/1.0',
    'Content-Type': 'application/x-apple-binary-plist'
}


# pylint: disable=too-few-public-methods
class AirPlayPlayer:
    """This class helps with playing media from an URL."""

    def __init__(self, loop, http):
        """Initialize a new AirPlay instance."""
        self.loop = loop
        self.http = http

    async def play_url(self, url, position=0):
        """Play media from an URL on the device."""
        body = {
            'Content-Location': url,
            'Start-Position': position,
            'X-Apple-Session-ID': str(uuid4()),
            }

        # pylint: disable=no-member
        await self.http.post_data(
            'play',
            headers=HEADERS,
            data=plistlib.dumps(body, fmt=plistlib.FMT_BINARY),
            timeout=TIMEOUT)
        await self._wait_for_media_to_end()

    # Poll playback-info to find out if something is playing. It might take
    # some time until the media starts playing, give it 5 seconds (attempts)
    async def _wait_for_media_to_end(self):
        attempts = 5
        video_started = False

        while True:
            data, status = await self.http.get_data('playback-info')

            if status == 403:
                raise exceptions.NoCredentialsError(
                    'device authentication required')

            _LOGGER.debug('Playback-info (%d): %s', status, data)

            parsed = plistlib.loads(data)

            # duration is only available if something is playing
            if 'duration' in parsed:
                video_started = True
                attempts = -1
            else:
                video_started = False
                if attempts >= 0:
                    attempts -= 1

            if not video_started and attempts < 0:
                _LOGGER.debug('media playback ended')
                break

            await asyncio.sleep(1, loop=self.loop)
