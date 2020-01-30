"""Implementation of the DMAP protocol used by ATV 1, 2 and 3."""

import logging
import asyncio

from aiohttp.client_exceptions import ClientError

from pyatv import (exceptions, convert, net)
from pyatv.cache import Cache
from pyatv.const import Protocol, MediaType, RepeatState, ShuffleState
from pyatv.dmap import (parser, tags)
from pyatv.dmap.daap import DaapRequester
from pyatv.net import HttpSession
from pyatv.interface import (AppleTV, RemoteControl, Metadata,
                             Playing, PushUpdater, ArtworkInfo)

_LOGGER = logging.getLogger(__name__)

_PSU_CMD = 'ctrl-int/1/playstatusupdate?[AUTH]&revision-number={0}'
_ARTWORK_CMD = 'ctrl-int/1/nowplayingartwork?mw=1024&mh=576&[AUTH]'
_CTRL_PROMPT_CMD = 'ctrl-int/1/controlpromptentry?[AUTH]&prompt-id=0'


class BaseDmapAppleTV:
    """Common protocol logic used to interact with an Apple TV."""

    def __init__(self, requester):
        """Initialize a new Apple TV base implemenation."""
        self.daap = requester
        self.playstatus_revision = 0
        self.latest_hash = None

    async def playstatus(self, use_revision=False, timeout=None):
        """Request raw data about what is currently playing.

        If use_revision=True, this command will "block" until playstatus
        changes on the device.

        Must be logged in.
        """
        cmd_url = _PSU_CMD.format(
            self.playstatus_revision if use_revision else 0)
        resp = await self.daap.get(cmd_url, timeout=timeout)
        self.playstatus_revision = parser.first(resp, 'cmst', 'cmsr')
        playing = DmapPlaying(resp)
        self.latest_hash = playing.hash
        return playing

    async def artwork(self):
        """Return an image file (png) for what is currently playing.

        None is returned if no artwork is available. Must be logged in.
        """
        art = await self.daap.get(_ARTWORK_CMD, daap_data=False)
        return art if art != b'' else None

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


# pylint: disable=too-many-public-methods
class DmapRemoteControl(RemoteControl):
    """Implementation of API for controlling an Apple TV."""

    def __init__(self, apple_tv):
        """Initialize remote control instance."""
        super().__init__()
        self.apple_tv = apple_tv

    async def up(self):
        """Press key up."""
        await self._send_commands(
            self._move('Down', 0, 20, 275),
            self._move('Move', 1, 20, 270),
            self._move('Move', 2, 20, 265),
            self._move('Move', 3, 20, 260),
            self._move('Move', 4, 20, 255),
            self._move('Move', 5, 20, 250),
            self._move('Up', 6, 20, 250))

    async def down(self):
        """Press key down."""
        await self._send_commands(
            self._move('Down', 0, 20, 250),
            self._move('Move', 1, 20, 255),
            self._move('Move', 2, 20, 260),
            self._move('Move', 3, 20, 265),
            self._move('Move', 4, 20, 270),
            self._move('Move', 5, 20, 275),
            self._move('Up', 6, 20, 275))

    async def left(self):
        """Press key left."""
        await self._send_commands(
            self._move('Down', 0, 75, 100),
            self._move('Move', 1, 70, 100),
            self._move('Move', 3, 65, 100),
            self._move('Move', 4, 60, 100),
            self._move('Move', 5, 55, 100),
            self._move('Move', 6, 50, 100),
            self._move('Up', 7, 50, 100))

    async def right(self):
        """Press key right."""
        await self._send_commands(
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

    async def _send_commands(self, *cmds):
        for cmd in cmds:
            await self.apple_tv.controlprompt_data(cmd)

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

    def volume_up(self):
        """Press key volume up."""
        # DMAP support unknown
        raise exceptions.NotSupportedError()

    def volume_down(self):
        """Press key volume down."""
        # DMAP support unknown
        raise exceptions.NotSupportedError()

    def home(self):
        """Press key home."""
        # DMAP support unknown
        raise exceptions.NotSupportedError()

    def home_hold(self):
        """Hold key home."""
        # DMAP support unknown
        raise exceptions.NotSupportedError()

    def suspend(self):
        """Suspend the device."""
        # Not supported by DMAP
        raise exceptions.NotSupportedError()

    def wakeup(self):
        """Wake up the device."""
        raise exceptions.NotSupportedError()

    def set_position(self, pos):
        """Seek in the current playing media."""
        time_in_ms = int(pos)*1000
        return self.apple_tv.set_property('dacp.playingtime', time_in_ms)

    def set_shuffle(self, shuffle_state):
        """Change shuffle mode to on or off."""
        state = 0 if shuffle_state == ShuffleState.Off else 1
        return self.apple_tv.set_property('dacp.shufflestate', state)

    def set_repeat(self, repeat_state):
        """Change repeat mode."""
        return self.apple_tv.set_property(
            'dacp.repeatstate', repeat_state.value)


class DmapPlaying(Playing):
    """Implementation of API for retrieving what is playing."""

    def __init__(self, playstatus):
        """Initialize playing instance."""
        super().__init__()
        self.playstatus = playstatus

    @property
    def media_type(self):
        """Type of media is currently playing, e.g. video, music."""
        state = parser.first(self.playstatus, 'cmst', 'caps')
        if not state:
            return MediaType.Unknown

        mediakind = parser.first(self.playstatus, 'cmst', 'cmmk')
        if mediakind is not None:
            return convert.media_kind(mediakind)

        # Fallback: if artist or album exists we assume music (not present
        # for video)
        if self.artist or self.album:
            return MediaType.Music

        return MediaType.Video

    @property
    def device_state(self):
        """Device state, e.g. playing or paused."""
        state = parser.first(self.playstatus, 'cmst', 'caps')
        return convert.playstate(state)

    @property
    def title(self):
        """Title of the current media, e.g. movie or song name."""
        return parser.first(self.playstatus, 'cmst', 'cann')

    @property
    def artist(self):
        """Arist of the currently playing song."""
        return parser.first(self.playstatus, 'cmst', 'cana')

    @property
    def album(self):
        """Album of the currently playing song."""
        return parser.first(self.playstatus, 'cmst', 'canl')

    @property
    def genre(self):
        """Genre of the currently playing song."""
        return parser.first(self.playstatus, 'cmst', 'cang')

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
        state = parser.first(self.playstatus, 'cmst', 'cash')
        if state is None or state == 0:
            return ShuffleState.Off

        # DMAP does not support the "albums" state and will always report
        # "songs" if shuffle is active
        return ShuffleState.Songs

    @property
    def repeat(self):
        """Repeat mode."""
        state = parser.first(self.playstatus, 'cmst', 'carp')
        if state is None:
            return RepeatState.Off
        return RepeatState(state)

    def _get_time_in_seconds(self, tag):
        time = parser.first(self.playstatus, 'cmst', tag)
        return convert.ms_to_s(time)


class DmapMetadata(Metadata):
    """Implementation of API for retrieving metadata from an Apple TV."""

    def __init__(self, identifier, apple_tv):
        """Initialize metadata instance."""
        super().__init__(identifier)
        self.apple_tv = apple_tv
        self.artwork_cache = Cache(limit=4)

    async def artwork(self):
        """Return artwork for what is currently playing (or None)."""
        # Having to fetch "playing" here is not ideal, but an identifier is
        # needed and we cannot trust any previous identifiers. So we have to do
        # this until a better solution comes along.
        playing = await self.playing()
        identifier = playing.hash
        if identifier in self.artwork_cache:
            _LOGGER.debug('Retrieved artwork %s from cache', identifier)
            return self.artwork_cache.get(identifier)

        artwork = await self._fetch_artwork()
        if artwork:
            self.artwork_cache.put(identifier, artwork)
            return artwork

        return None

    async def _fetch_artwork(self):
        _LOGGER.debug('Fetching artwork')
        data = await self.apple_tv.artwork()
        if data:
            return ArtworkInfo(data, 'image/png')
        return None

    @property
    def artwork_id(self):
        """Return a unique identifier for current artwork."""
        return self.apple_tv.latest_hash

    async def playing(self):
        """Return current device state."""
        return await self.apple_tv.playstatus()


class DmapPushUpdater(PushUpdater):
    """Implementation of API for handling push update from an Apple TV."""

    def __init__(self, loop, apple_tv, listener):
        """Initialize a new DmapPushUpdater instance."""
        super().__init__()
        self._loop = loop
        self._atv = apple_tv
        self._listener = listener
        self._future = None
        self._initial_delay = 0

    @property
    def active(self):
        """Return if push updater has been started."""
        return self._future is not None

    def start(self, initial_delay=0):
        """Wait for push updates from device.

        Will throw NoAsyncListenerError if no listener has been set.
        """
        if self.listener is None:
            raise exceptions.NoAsyncListenerError()
        if self.active:
            return

        # Always start with 0 to trigger an immediate response for the
        # first request
        self._atv.playstatus_revision = 0

        # Delay before restarting after an error
        self._initial_delay = initial_delay

        self._future = asyncio.ensure_future(self._poller(), loop=self._loop)

    def stop(self):
        """No longer forward updates to listener."""
        if self._future is not None:
            self._future.cancel()
            self._future = None

    async def _poller(self):
        first_call = True

        while True:
            # Sleep some time before waiting for updates
            if not first_call and self._initial_delay > 0:
                _LOGGER.debug('Initial delay set to %d', self._initial_delay)
                await asyncio.sleep(self._initial_delay, loop=self._loop)
                first_call = False

            try:
                _LOGGER.debug('Waiting for playstatus updates')
                playstatus = await self._atv.playstatus(
                    use_revision=True, timeout=0)

                self._loop.call_soon(
                    self.listener.playstatus_update, self, playstatus)
            except asyncio.CancelledError:
                break

            except ClientError as ex:
                _LOGGER.exception('A communication error happened')
                if self._listener and self._listener.listener:
                    self._loop.call_soon(
                        self._listener.listener.connection_lost, ex)

                break

            # It is not pretty to disable pylint here, but we must catch _all_
            # exceptions to keep the API.
            except Exception as ex:  # pylint: disable=broad-except
                _LOGGER.debug('Playstatus error occurred: %s', ex)
                self._loop.call_soon(self.listener.playstatus_error, self, ex)

        self._future = None


class DmapAppleTV(AppleTV):
    """Implementation of API support for Apple TV."""

    # This is a container class so it's OK with many attributes
    # pylint: disable=too-many-instance-attributes
    def __init__(self, loop, session, config, airplay):
        """Initialize a new Apple TV."""
        super().__init__()
        self._session = session

        self._dmap_service = config.get_service(Protocol.DMAP)
        daap_http = HttpSession(
            session,
            'http://{0}:{1}/'.format(config.address, self._dmap_service.port))
        self._requester = DaapRequester(
            daap_http, self._dmap_service.credentials)

        self._apple_tv = BaseDmapAppleTV(self._requester)
        self._dmap_remote = DmapRemoteControl(self._apple_tv)
        self._dmap_metadata = DmapMetadata(config.identifier, self._apple_tv)
        self._dmap_push_updater = DmapPushUpdater(loop, self._apple_tv, self)
        self._airplay = airplay

    def connect(self):
        """Initiate connection to device.

        No need to call it yourself, it's done automatically.
        """
        return self._requester.login()

    async def close(self):
        """Close connection and release allocated resources."""
        if net.is_custom_session(self._session):
            await self._session.close()
        if self.listener:
            self.listener.connection_closed()

    @property
    def service(self):
        """Return service used to connect to the Apple TV.."""
        return self._dmap_service

    @property
    def remote_control(self):
        """Return API for controlling the Apple TV."""
        return self._dmap_remote

    @property
    def metadata(self):
        """Return API for retrieving metadata from Apple TV."""
        return self._dmap_metadata

    @property
    def push_updater(self):
        """Return API for handling push update from the Apple TV."""
        return self._dmap_push_updater

    @property
    def stream(self):
        """Return API for streaming media."""
        return self._airplay
