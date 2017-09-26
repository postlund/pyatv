"""Play media on a device by sending an URL."""

import logging
import asyncio
import plistlib

from aiohttp import ClientSession

from pyatv import const

_LOGGER = logging.getLogger(__name__)

# This is the default port. It is also included in the Bonjour service
# _airplay._tcp, so it might be a good idea to get it from there in the
# future.
AIRPLAY_PORT = 7000

TIMEOUT = 10


# TODO: Use net.HttpSession instead of ClientSession
# pylint: disable=too-few-public-methods
class AirPlayPlayer:
    """This class helps with playing media from an URL."""

    def __init__(self, loop, address, port=7000):
        """Initialize a new AirPlay instance."""
        self.loop = loop
        self.address = address
        self.port = port

    @asyncio.coroutine
    def play_url(self, url, position=0):
        """Play media from an URL on the device."""
        headers = {'User-Agent': 'MediaControl/1.0',
                   'Content-Type': 'text/parameters'}
        body = "Content-Location: {}\nStart-Position: {}\n\n".format(
            url, position)

        address = self._url(self.port, 'play')
        _LOGGER.debug('AirPlay %s to %s', url, address)

        resp = None
        try:
            session = ClientSession(loop=self.loop)
            resp = yield from session.post(
                address, headers=headers, data=body, timeout=TIMEOUT)
            yield from self._wait_for_media_to_end(session)
        finally:
            if resp is not None:
                resp.close()
            # Apple TV 3 Gen have a bug. It stays in playing state forever
            # after stream finished. We need close session every time when
            # video stops to fix it.
            session.close()

    def _url(self, port, command):
        return 'http://{}:{}/{}'.format(self.address, port, command)

    # Poll playback-info to find out if something is playing.
    @asyncio.coroutine
    def _wait_for_media_to_end(self, session):
        address = self._url(self.port, 'playback-info')
        play_state = const.PLAY_STATE_LOADING
        while True:
            info = None
            try:
                info = yield from session.get(address)
                data = yield from info.content.read()
                parsed = plistlib.loads(data)

                if play_state == const.PLAY_STATE_LOADING:
                    if 'duration' in parsed:
                        play_state = const.PLAY_STATE_PLAYING
                    elif 'readyToPlay' not in parsed:
                        play_state = const.PLAY_STATE_NO_MEDIA
                        break
                elif play_state == const.PLAY_STATE_PLAYING:
                    if 'duration' not in parsed:
                        play_state = const.PLAY_STATE_NO_MEDIA
                        break

            finally:
                if info is not None:
                    info.close()

            yield from asyncio.sleep(1, loop=self.loop)
