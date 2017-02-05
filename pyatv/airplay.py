"""Play media on a device by sending an URL."""

import logging
import asyncio
import plistlib

from aiohttp import ClientSession

_LOGGER = logging.getLogger(__name__)

# This is the default port. It is also included in the Bonjour service
# _airplay._tcp, so it might be a good idea to get it from there in the
# future.
AIRPLAY_PORT = 7000

TIMEOUT = 10


# pylint: disable=too-few-public-methods
class AirPlay:
    """This class helps with playing media from an URL."""

    def __init__(self, loop, address):
        """Initialize a new AirPlay instance."""
        self.loop = loop
        self.address = address
        self.session = None

    @asyncio.coroutine
    def play_url(self, url, start_position, port=AIRPLAY_PORT):
        """Play media from an URL on the device."""
        headers = {'User-Agent': 'MediaControl/1.0',
                   'Content-Type': 'text/parameters'}
        body = "Content-Location: {}\nStart-Position: {}\n\n".format(
            url, start_position)

        # Use a new session for this so we can close it when playback has
        # finished, otherwise the device will "hang" with a black screen for a
        # while.
        self.session = ClientSession(loop=self.loop)

        address = self._url(port, 'play')
        _LOGGER.debug('AirPlay %s to %s', url, address)

        resp = yield from self.session.post(
            address, headers=headers, data=body, timeout=TIMEOUT)
        try:
            yield from self._wait_for_media_to_end(port)
        finally:
            yield from resp.release()
            yield from self.session.close()

    def _url(self, port, command):
        return 'http://{}:{}/{}'.format(self.address, port, command)

    # Poll playback-info to find out if something is playing. It might take
    # some time until the media starts playing, give it 5 seconds (attempts)
    @asyncio.coroutine
    def _wait_for_media_to_end(self, port):
        address = self._url(port, 'playback-info')
        attempts = 5
        video_started = False
        while True:
            info = yield from self.session.get(address)
            try:
                data = yield from info.content.read()
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

            finally:
                yield from info.release()

            yield from asyncio.sleep(1, self.loop)
