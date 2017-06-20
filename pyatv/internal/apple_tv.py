"""Implementation of the protocol used to interact with an Apple TV.

Only verified to work with a 3rd generation device. Classes should be
extracted and adjusted for differences if needed, to support newer/older
generations of devices. Everything is however left here for now.
"""

import logging
import asyncio
import binascii
import hashlib

from pyatv import (const, exceptions, dmap, tags, convert)
from pyatv.airplay import player
from pyatv.daap import DaapRequester
from pyatv.net import HttpSession
from pyatv.interface import (AppleTV, RemoteControl, Metadata,
                             Playing, PushUpdater, AirPlay)
from pyatv.airplay.srp import (SRPAuthHandler, new_credentials)
from pyatv.airplay.auth import (AuthenticationVerifier, DeviceAuthenticator)

_LOGGER = logging.getLogger(__name__)

_PSU_CMD = 'ctrl-int/1/playstatusupdate?[AUTH]&revision-number={0}'
_ARTWORK_CMD = 'ctrl-int/1/nowplayingartwork?mw=1024&mh=576&[AUTH]'
_CTRL_PROMPT_CMD = 'ctrl-int/1/controlpromptentry?[AUTH]&prompt-id=0'


class BaseAppleTV:
    """Common protocol logic used to interact with an Apple TV."""

    def __init__(self, requester):
        """Initialize a new Apple TV base implemenation."""
        self.daap = requester
        self.playstatus_revision = 0

    def server_info(self):
        """Request and return server information."""
        return (yield from self.daap.get(
            'server-info', session=False, login_id=False))

    @asyncio.coroutine
    def playstatus(self, use_revision=False, timeout=None):
        """Request raw data about what is currently playing.

        If use_revision=True, this command will "block" until playstatus
        changes on the device.

        Must be logged in.
        """
        cmd_url = _PSU_CMD.format(
            self.playstatus_revision if use_revision else 0)
        resp = yield from self.daap.get(cmd_url, timeout=timeout)
        self.playstatus_revision = dmap.first(resp, 'cmst', 'cmsr')
        return resp

    def artwork_url(self):
        """Return URL to current artwork.

        As as valid session id is necessary, the URL will only be valid
        if logged in.
        """
        return self.daap.get_url(_ARTWORK_CMD)

    @asyncio.coroutine
    def artwork(self):
        """Return an image file (png) for what is currently playing.

        None is returned if no artwork is available. Must be logged in.
        """
        art = yield from self.daap.get(_ARTWORK_CMD, daap_data=False)
        return art if art != b'' else None

    def playqueue(self):
        """Return current playqueue. Must be logged in."""
        return self.daap.post('playqueue-contents?[AUTH]')

    def ctrl_int_cmd(self, cmd):
        """Perform a "ctrl-int" command."""
        cmd_url = 'ctrl-int/1/{}?[AUTH]&prompt-id=0'.format(cmd)
        return self.daap.post(cmd_url)

    def controlprompt_cmd(self, cmd):
        """Perform a "controlpromptentry" command."""
        data = tags.string_tag('cmbe', cmd) + tags.uint8_tag('cmcc', 0)
        return self.daap.post(_CTRL_PROMPT_CMD, data=data)

    def controlprompt_data(self, data):
        """Perform a "controlpromptentry" command."""
        return self.daap.post(_CTRL_PROMPT_CMD, data=data)

    def set_property(self, prop, value):
        """Change value of a DAAP property, e.g. volume or media position."""
        cmd_url = 'ctrl-int/1/setproperty?{}={}&[AUTH]'.format(
            prop, value)
        return self.daap.post(cmd_url)


class RemoteControlInternal(RemoteControl):
    """Implementation of API for controlling an Apple TV."""

    def __init__(self, apple_tv):
        """Initialize remote control instance."""
        super().__init__()
        self.apple_tv = apple_tv

    @asyncio.coroutine
    def up(self):
        """Press key up."""
        yield from self._send_commands(
            self._move('Down', 0, 20, 275),
            self._move('Move', 1, 20, 270),
            self._move('Move', 2, 20, 265),
            self._move('Move', 3, 20, 260),
            self._move('Move', 4, 20, 255),
            self._move('Move', 5, 20, 250),
            self._move('Up', 6, 20, 250))

    @asyncio.coroutine
    def down(self):
        """Press key down."""
        yield from self._send_commands(
            self._move('Down', 0, 20, 250),
            self._move('Move', 1, 20, 255),
            self._move('Move', 2, 20, 260),
            self._move('Move', 3, 20, 265),
            self._move('Move', 4, 20, 270),
            self._move('Move', 5, 20, 275),
            self._move('Up', 6, 20, 275))

    @asyncio.coroutine
    def left(self):
        """Press key left."""
        yield from self._send_commands(
            self._move('Down', 0, 75, 100),
            self._move('Move', 1, 70, 100),
            self._move('Move', 3, 65, 100),
            self._move('Move', 4, 60, 100),
            self._move('Move', 5, 55, 100),
            self._move('Move', 6, 50, 100),
            self._move('Up', 7, 50, 100))

    @asyncio.coroutine
    def right(self):
        """Press key right."""
        yield from self._send_commands(
            self._move('Down', 0, 50, 100),
            self._move('Move', 1, 55, 100),
            self._move('Move', 3, 60, 100),
            self._move('Move', 4, 65, 100),
            self._move('Move', 5, 70, 100),
            self._move('Move', 6, 75, 100),
            self._move('Up', 7, 75, 100))

    @staticmethod
    def _move(direction, time, point1, point2):
        data = 'touch{0}&time={1}&point={2},{3}'.format(
            direction, time, point1, point2)
        return tags.uint8_tag('cmcc', 0x30) + tags.string_tag('cmbe', data)

    @asyncio.coroutine
    def _send_commands(self, *cmds):
        for cmd in cmds:
            yield from self.apple_tv.controlprompt_data(cmd)

    def play(self):
        """Press key play."""
        return self.apple_tv.ctrl_int_cmd('play')

    def pause(self):
        """Press key pause."""
        return self.apple_tv.ctrl_int_cmd('pause')

    def stop(self):
        """Press key stop."""
        return self.apple_tv.ctrl_int_cmd('stop')

    def next(self):
        """Press key next."""
        return self.apple_tv.ctrl_int_cmd('nextitem')

    def previous(self):
        """Press key previous."""
        return self.apple_tv.ctrl_int_cmd('previtem')

    def select(self):
        """Press key select."""
        return self.apple_tv.controlprompt_cmd('select')

    def menu(self):
        """Press key menu."""
        return self.apple_tv.controlprompt_cmd('menu')

    def top_menu(self):
        """Press key topmenu."""
        return self.apple_tv.controlprompt_cmd('topmenu')

    def set_position(self, pos):
        """Seek in the current playing media."""
        time_in_ms = int(pos)*1000
        return self.apple_tv.set_property('dacp.playingtime', time_in_ms)

    def set_shuffle(self, is_on):
        """Change shuffle mode to on or off."""
        state = 1 if is_on else 0
        return self.apple_tv.set_property('dacp.shufflestate', state)

    def set_repeat(self, repeat_mode):
        """Change repeat mode."""
        return self.apple_tv.set_property('dacp.repeatstate', repeat_mode)


class PlayingInternal(Playing):
    """Implementation of API for retrieving what is playing."""

    def __init__(self, playstatus):
        """Initialize playing instance."""
        super().__init__()
        self.playstatus = playstatus

    @property
    def media_type(self):
        """Type of media is currently playing, e.g. video, music."""
        state = dmap.first(self.playstatus, 'cmst', 'caps')
        if not state:
            return const.MEDIA_TYPE_UNKNOWN

        mediakind = dmap.first(self.playstatus, 'cmst', 'cmmk')
        if mediakind is not None:
            return convert.media_kind(mediakind)

        # Fallback: if artist or album exists we assume music (not present
        # for video)
        if self.artist or self.album:
            return const.MEDIA_TYPE_MUSIC

        return const.MEDIA_TYPE_VIDEO

    @property
    def play_state(self):
        """Play state, e.g. playing or paused."""
        state = dmap.first(self.playstatus, 'cmst', 'caps')
        return convert.playstate(state)

    @property
    def title(self):
        """Title of the current media, e.g. movie or song name."""
        return dmap.first(self.playstatus, 'cmst', 'cann')

    @property
    def artist(self):
        """Arist of the currently playing song."""
        return dmap.first(self.playstatus, 'cmst', 'cana')

    @property
    def album(self):
        """Album of the currently playing song."""
        return dmap.first(self.playstatus, 'cmst', 'canl')

    @property
    def total_time(self):
        """Total play time in seconds."""
        return self._get_time_in_seconds('cast')

    @property
    def position(self):
        """Position in the playing media (seconds)."""
        return self.total_time - self._get_time_in_seconds('cant')

    @property
    def shuffle(self):
        """If shuffle is enabled or not."""
        return bool(dmap.first(self.playstatus, 'cmst', 'cash'))

    @property
    def repeat(self):
        """Repeat mode."""
        return dmap.first(self.playstatus, 'cmst', 'carp')

    def _get_time_in_seconds(self, tag):
        time = dmap.first(self.playstatus, 'cmst', tag)
        return convert.ms_to_s(time)


class MetadataInternal(Metadata):
    """Implementation of API for retrieving metadata from an Apple TV."""

    def __init__(self, apple_tv, daap):
        """Initialize metadata instance."""
        super().__init__()
        self.apple_tv = apple_tv

        # Strip port number and base hash only on address
        self._device_id = hashlib.sha256(
            daap.base_url.split(':')[0].encode('utf-8')).hexdigest()

    @property
    def device_id(self):
        """Return a unique identifier for current device."""
        return self._device_id

    def artwork(self):
        """Return artwork for what is currently playing (or None)."""
        return self.apple_tv.artwork()

    @asyncio.coroutine
    def artwork_url(self):
        """Return artwork URL for what is currently playing."""
        return self.apple_tv.artwork_url()

    @asyncio.coroutine
    def playing(self):
        """Return current device state."""
        playstatus = yield from self.apple_tv.playstatus()
        return PlayingInternal(playstatus)


class PushUpdaterInternal(PushUpdater):
    """Implementation of API for handling push update from an Apple TV."""

    def __init__(self, loop, apple_tv):
        """Initialize a new PushUpdaterInternal instance."""
        self._loop = loop
        self._atv = apple_tv
        self._future = None
        self.__listener = None

    @property
    def listener(self):
        """Receiver of push updates."""
        return self.__listener

    @listener.setter
    def listener(self, listener):
        """Change active listener to push updates.

        Will throw AsyncUpdaterRunningError if push updates is enabled.
        """
        if self._future is not None:
            raise exceptions.AsyncUpdaterRunningError

        self.__listener = listener

    def start(self, initial_delay=0):
        """Wait for push updates from device.

        Will throw NoAsyncListenerError if no listner has been set.
        """
        if self._future is not None:
            raise exceptions.NoAsyncListenerError

        # If ensure_future, use that instead of async
        if hasattr(asyncio, 'ensure_future'):
            run_async = getattr(asyncio, 'ensure_future')
        else:
            run_async = asyncio.async  # pylint: disable=no-member

        # Always start with 0 to trigger an immediate response for the
        # first request
        self._atv.playstatus_revision = 0

        # This for some reason fails on travis but not in other places.
        # Why is that (same python version)?
        # pylint: disable=deprecated-method
        self._future = run_async(self._poller(initial_delay),
                                 loop=self._loop)
        return self._future

    def stop(self):
        """No longer wait for push updates."""
        if self._future is not None:
            # TODO: pylint does not seem to figure out that cancel exists?
            self._future.cancel()  # pylint: disable=no-member
            self._future = None

    @asyncio.coroutine
    def _poller(self, initial_delay):
        # Sleep some time before waiting for updates
        if initial_delay > 0:
            _LOGGER.debug('Initial delay set to %d', initial_delay)
            yield from asyncio.sleep(initial_delay, loop=self._loop)

        while True:
            try:
                _LOGGER.debug('Waiting for playstatus updates')
                playstatus = yield from self._atv.playstatus(
                    use_revision=True, timeout=0)

                self._loop.call_soon(self.listener.playstatus_update,
                                     self, PlayingInternal(playstatus))
            except asyncio.CancelledError:
                break

            # It is not pretty to disable pylint here, but we must catch _all_
            # exceptions to keep the API.
            except Exception as ex:  # pylint: disable=broad-except
                _LOGGER.debug('Playstatus error occurred: %s', ex)
                self._loop.call_soon(self.listener.playstatus_error, self, ex)
                break

        self._future = None


# pylint: disable=too-few-public-methods
class AirPlayInternal(AirPlay):
    """Implementation of API for AirPlay support."""

    def __init__(self, http, airplay_player):
        """Initialize a new AirPlayInternal instance."""
        self.player = airplay_player
        self.identifier = None
        self.srp = SRPAuthHandler()
        self.verifier = AuthenticationVerifier(http, self.srp)
        self.auther = DeviceAuthenticator(http, self.srp)

    @asyncio.coroutine
    def generate_credentials(self):
        """Create new credentials for authentication.

        Credentials that have been authenticated shall be saved and loaded with
        load_credentials before playing anything. If credentials are lost,
        authentication must be performed again.
        """
        identifier, seed = new_credentials()
        return '{0}:{1}'.format(identifier, seed.decode().upper())

    @asyncio.coroutine
    def load_credentials(self, credentials):
        """Load existing credentials."""
        split = credentials.split(':')
        self.identifier = split[0]
        self.srp.initialize(binascii.unhexlify(split[1]))
        _LOGGER.debug('Loaded AirPlay credentials: %s', credentials)

    def verify_authenticated(self):
        """Check if loaded credentials are verified."""
        return self.verifier.verify_authed()

    def start_authentication(self):
        """Begin authentication proces (show PIN on screen)."""
        return self.auther.start_authentication()

    def finish_authentication(self, pin):
        """End authentication process with PIN code."""
        return self.auther.finish_authentication(self.identifier, pin)

    @asyncio.coroutine
    def play_url(self, url, **kwargs):
        """Play media from an URL on the device.

        Note: This method will not yield until the media has finished playing.
        The Apple TV requires the request to stay open during the entire
        play duration.
        """
        # If credentials have been loaded, do device verification first
        if self.identifier:
            yield from self.verify_authenticated()

        position = 0 if 'position' not in kwargs else int(kwargs['position'])
        return (yield from self.player.play_url(url, position))


class AppleTVInternal(AppleTV):
    """Implementation of API support for Apple TV."""

    # This is a container class so it's OK with many attributes
    # pylint: disable=too-many-instance-attributes
    def __init__(self, loop, session, details):
        """Initialize a new Apple TV."""
        super().__init__()
        self._session = session

        daap_http = HttpSession(
            session, 'http://{0}:{1}/'.format(details.address, details.port))
        self._requester = DaapRequester(daap_http, details.login_id)

        self._apple_tv = BaseAppleTV(self._requester)
        self._atv_remote = RemoteControlInternal(self._apple_tv)
        self._atv_metadata = MetadataInternal(self._apple_tv, daap_http)
        self._atv_push_updater = PushUpdaterInternal(loop, self._apple_tv)

        airplay_player = player.AirPlayPlayer(
            loop, session, details.address, details.airplay_port)
        airplay_http = HttpSession(
            session, 'http://{0}:{1}/'.format(
                details.address, details.airplay_port))
        self._airplay = AirPlayInternal(airplay_http, airplay_player)

    def login(self):
        """Perform an explicit login.

        Not needed as login is performed automatically.
        """
        return self._requester.login()

    @asyncio.coroutine
    def logout(self):
        """Perform an explicit logout.

        Must be done when session is no longer needed to not leak resources.
        """
        self._session.close()

    @property
    def remote_control(self):
        """Return API for controlling the Apple TV."""
        return self._atv_remote

    @property
    def metadata(self):
        """Return API for retrieving metadata from Apple TV."""
        return self._atv_metadata

    @property
    def push_updater(self):
        """Return API for handling push update from the Apple TV."""
        return self._atv_push_updater

    @property
    def airplay(self):
        """Return API for working with AirPlay."""
        return self._airplay
