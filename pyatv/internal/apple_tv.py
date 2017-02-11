"""Implementation of the protocol used to interact with an Apple TV.

Only verified to work with a 3rd generation device. Classes should be
extracted and adjusted for differences if needed, to support newer/older
generations of devices. Everything is however left here for now.
"""

import logging
import asyncio

from pyatv import (const, exceptions, dmap, tags, interface, convert)
from pyatv.interface import (AppleTV, RemoteControl, Metadata, Playing)


_LOGGER = logging.getLogger(__name__)

_ARTWORK_CMD = 'ctrl-int/1/nowplayingartwork?mw=1024&mh=576&[AUTH]'


class BaseAppleTV:
    """Common protocol logic used to interact with an Apple TV."""

    def __init__(self, requester):
        """Initialize a new Apple TV base implemenation."""
        self.daap = requester

    def server_info(self):
        """Request and return server information."""
        return (yield from self.daap.get(
            'server-info', session=False, login_id=False))

    def playstatus(self):
        """Request raw data about what is currently playing.

        Must be logged in.
        """
        cmd_url = 'ctrl-int/1/playstatusupdate?[AUTH]&revision-number=0'
        return self.daap.get(cmd_url)

    # TODO: currenly not used, needed when non-polling API is implemented
    @asyncio.coroutine
    def controlpromptupdate(self):
        """Request session id used to control a device. Must be logged in."""
        cmd_url = 'controlpromptupdate?[AUTH]&prompt-id=0'
        resp = yield from self.daap.post(cmd_url)
        self.daap.revision_number = dmap.first(resp, 'cmcp', 'miid')
        _LOGGER.info('Got revision id %d for controlpromptupdate',
                     self.daap.revision_number)
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
        data = tags.string_tag('cmbe', cmd) + tags.string_tag('cmcc', '0')
        cmd_url = 'ctrl-int/1/controlpromptentry?[AUTH]&prompt-id=0'
        return self.daap.post(cmd_url, data=data)

    def set_property(self, prop, value):
        """Change value of a DAAP property, e.g. volume or media position."""
        cmd_url = 'ctrl-int/1/setproperty?{}={}&[AUTH]&prompt-id=0'.format(
            prop, value)
        return self.daap.post(cmd_url)


class RemoteControlInternal(RemoteControl):
    """Implementation of API for controlling an Apple TV."""

    def __init__(self, apple_tv, airplay):
        """Initialize remote control instance."""
        super().__init__()
        self.apple_tv = apple_tv
        self.airplay = airplay

    def up(self):
        """Press key up."""
        raise exceptions.NotSupportedError

    def down(self):
        """Press key down."""
        raise exceptions.NotSupportedError

    def left(self):
        """Press key left."""
        raise exceptions.NotSupportedError

    def right(self):
        """Press key right."""
        raise exceptions.NotSupportedError

    def play(self):
        """Press key play."""
        return self.apple_tv.ctrl_int_cmd('play')

    def pause(self):
        """Press key pause."""
        return self.apple_tv.ctrl_int_cmd('pause')

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

    def play_url(self, url, start_position, **kwargs):
        """Play media from an URL on the device.

        Note: This method will not yield until the media has finished playing.
        The Apple TV requires the request to stay open during the entire
        play duration.
        """
        # AirPlay is separate from DAAP, so to make it easier to test the port
        # can be overriden to something else. NOT part of the public API!
        import pyatv.airplay
        port_override = 'port' in kwargs
        port = kwargs['port'] if port_override else pyatv.airplay.AIRPLAY_PORT
        return self.airplay.play_url(url, int(start_position), port)


class PlayingInternal(Playing):
    """Implementation of API for retrieving what is playing."""

    def __init__(self, apple_tv, playstatus):
        """Initialize playing instance."""
        super().__init__()
        self.apple_tv = apple_tv
        self.playstatus = playstatus

    def __str__(self):
        """Convert this playing object to a readable string."""
        def _to_str(value_mapping):
            return '{}: {}'.format(value_mapping, getattr(self, value_mapping))
        values = interface.retrieve_commands(self).keys()
        return '\n'.join(map(_to_str, sorted(values)))

    @property
    def media_type(self):
        """What type of media is currently playing, e.g. video, music."""
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
        """Current play state, e.g. playing or paused."""
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
        """Album of the currently playing song.."""
        return dmap.first(self.playstatus, 'cmst', 'canl')

    @property
    def total_time(self):
        """Total play time in seconds."""
        return self._get_time_in_seconds('cast')

    @property
    def position(self):
        """Current position in the playing media (seconds)."""
        return self.total_time - self._get_time_in_seconds('cant')

    def _get_time_in_seconds(self, tag):
        time = dmap.first(self.playstatus, 'cmst', tag)
        return convert.ms_to_s(time)


class MetadataInternal(Metadata):
    """Implementation of API for retrieving metadata from an Apple TV."""

    def __init__(self, apple_tv):
        """Initialize metadata instance."""
        super().__init__()
        self.apple_tv = apple_tv

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
        return PlayingInternal(self.apple_tv, playstatus)

    def dev_playstatus(self):
        """Return raw playstatus response (developer command)."""
        return self.apple_tv.playstatus()

    def dev_playqueue(self):
        """Return raw playqueue response (developer command)."""
        return self.apple_tv.playqueue()

    def dev_server_info(self):
        """Return raw server-info sersponse (developer command)."""
        return self.apple_tv.server_info()


class AppleTVInternal(AppleTV):
    """Implementation of API support for Apple TV."""

    def __init__(self, session, requester, airplay):
        """Initialize a new Apple TV."""
        super().__init__()
        self.session = session
        self.requester = requester
        self.apple_tv = BaseAppleTV(self.requester)
        self.atv_remote = RemoteControlInternal(self.apple_tv, airplay)
        self.atv_metadata = MetadataInternal(self.apple_tv)

    def login(self):
        """Perform an explicit login.

        Not needed as login is performed automatically.
        """
        return self.requester.login()

    def logout(self):
        """Perform an explicit logout.

        Must be done when session is no longer needed to not leak resources.
        """
        return self.session.close()

    @property
    def remote_control(self):
        """Return API for controlling the Apple TV."""
        return self.atv_remote

    @property
    def metadata(self):
        """Return API for retrieving metadata from Apple TV."""
        return self.atv_metadata
