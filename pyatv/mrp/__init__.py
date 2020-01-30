"""Implementation of the MediaRemoteTV Protocol used by ATV4 and later."""

import math
import logging
import asyncio
import datetime

from pyatv import exceptions, net
from pyatv.const import (
    Protocol, MediaType, DeviceState, RepeatState, ShuffleState)
from pyatv.cache import Cache
from pyatv.mrp import (messages, protobuf)
from pyatv.mrp.srp import SRPAuthHandler
from pyatv.mrp.connection import MrpConnection
from pyatv.mrp.protocol import MrpProtocol
from pyatv.mrp.protobuf import CommandInfo_pb2, SetStateMessage_pb2
from pyatv.mrp.player_state import PlayerStateManager
from pyatv.interface import (AppleTV, RemoteControl, Metadata,
                             Playing, PushUpdater, ArtworkInfo)


_LOGGER = logging.getLogger(__name__)

# Source: https://github.com/Daij-Djan/DDHidLib/blob/master/usb_hid_usages.txt
_KEY_LOOKUP = {
    # name: [usage_page, usage, button hold time (seconds)]
    'up': [1, 0x8C, 0],
    'down': [1, 0x8D, 0],
    'left': [1, 0x8B, 0],
    'right': [1, 0x8A, 0],
    'stop': [12, 0xB7, 0],
    'next': [12, 0xB5, 0],
    'previous': [12, 0xB6, 0],
    'select': [1, 0x89, 0],
    'menu': [1, 0x86, 0],
    'topmenu': [12, 0x60, 0],
    'home': [12, 0x40, 1],
    'suspend': [1, 0x82, 0],
    'wakeup': [1, 0x83, 0],
    'volume_up': [12, 0xE9, 0],
    'volume_down': [12, 0xEA, 0],

    # 'mic': [12, 0x04, 0],  # Siri
}


# pylint: disable=too-many-public-methods
class MrpRemoteControl(RemoteControl):
    """Implementation of API for controlling an Apple TV."""

    def __init__(self, loop, protocol):
        """Initialize a new MrpRemoteControl."""
        self.loop = loop
        self.protocol = protocol

    async def _press_key(self, key, hold=False):
        lookup = _KEY_LOOKUP.get(key, None)
        if lookup:
            await self.protocol.send(
                messages.send_hid_event(lookup[0], lookup[1], True))
            if hold:
                await asyncio.sleep(lookup[2])
            await self.protocol.send(
                messages.send_hid_event(lookup[0], lookup[1], False))
        else:
            raise Exception('unknown key: ' + key)

    def up(self):
        """Press key up."""
        return self._press_key('up')

    def down(self):
        """Press key down."""
        return self._press_key('down')

    def left(self):
        """Press key left."""
        return self._press_key('left')

    def right(self):
        """Press key right."""
        return self._press_key('right')

    def play(self):
        """Press key play."""
        return self.protocol.send(messages.command(CommandInfo_pb2.Play))

    def pause(self):
        """Press key play."""
        return self.protocol.send(messages.command(CommandInfo_pb2.Pause))

    def stop(self):
        """Press key stop."""
        return self.protocol.send(messages.command(CommandInfo_pb2.Stop))

    def next(self):
        """Press key next."""
        return self.protocol.send(messages.command(CommandInfo_pb2.NextTrack))

    def previous(self):
        """Press key previous."""
        return self.protocol.send(
            messages.command(CommandInfo_pb2.PreviousTrack))

    def select(self):
        """Press key select."""
        return self._press_key('select')

    def menu(self):
        """Press key menu."""
        return self._press_key('menu')

    def volume_up(self):
        """Press key volume up."""
        return self._press_key('volume_up')

    def volume_down(self):
        """Press key volume down."""
        return self._press_key('volume_down')

    def home(self):
        """Press key home."""
        return self._press_key('home')

    def home_hold(self):
        """Hold key home."""
        return self._press_key('home', hold=True)

    def top_menu(self):
        """Go to main menu (long press menu)."""
        return self._press_key('topmenu')

    def suspend(self):
        """Suspend the device."""
        return self._press_key('suspend')

    def wakeup(self):
        """Wake up the device."""
        return self._press_key('wakeup')

    def set_position(self, pos):
        """Seek in the current playing media."""
        return self.protocol.send(messages.seek_to_position(pos))

    def set_shuffle(self, shuffle_state):
        """Change shuffle mode to on or off."""
        return self.protocol.send(messages.shuffle(shuffle_state))

    def set_repeat(self, repeat_state):
        """Change repeat state."""
        return self.protocol.send(messages.repeat(repeat_state))


class MrpPlaying(Playing):
    """Implementation of API for retrieving what is playing."""

    def __init__(self, state):
        """Initialize a new MrpPlaying."""
        self._state = state

    @property
    def media_type(self):
        """Type of media is currently playing, e.g. video, music."""
        if self._state.metadata:
            media_type = self._state.metadata.mediaType
            cim = protobuf.ContentItemMetadata
            if media_type == cim.Audio:
                return MediaType.Music
            if media_type == cim.Video:
                return MediaType.Video

        return MediaType.Unknown

    @property
    def device_state(self):  # pylint: disable=too-many-return-statements
        """Device state, e.g. playing or paused."""
        state = self._state.playback_state
        ssm = SetStateMessage_pb2.SetStateMessage
        if state is None:
            return DeviceState.Idle
        if state == ssm.Playing:
            return DeviceState.Playing
        if state == ssm.Paused:
            return DeviceState.Paused
        if state == ssm.Stopped:
            return DeviceState.Stopped
        if state == ssm.Interrupted:
            return DeviceState.Loading
        if state == ssm.Seeking:
            return DeviceState.Seeking

        return DeviceState.Paused

    @property
    def title(self):
        """Title of the current media, e.g. movie or song name."""
        return self._state.metadata_field('title')

    @property
    def artist(self):
        """Artist of the currently playing song."""
        return self._state.metadata_field('trackArtistName')

    @property
    def album(self):
        """Album of the currently playing song."""
        return self._state.metadata_field('albumName')

    @property
    def genre(self):
        """Genre of the currently playing song."""
        return self._state.metadata_field('genre')

    @property
    def total_time(self):
        """Total play time in seconds."""
        duration = self._state.metadata_field('duration')
        if duration is None or math.isnan(duration):
            return None
        return int(duration)

    @property
    def position(self):
        """Position in the playing media (seconds)."""
        # If we don't have reference time, we can't do anything
        if not self._state.timestamp:
            return None

        elapsed_time = self._state.metadata_field('elapsedTime')
        now = datetime.datetime.now()
        diff = (now - self._state.timestamp).total_seconds()

        # If elapsed time is available, we make the assumption that
        # it is zero (playback started at reference time)
        elapsed_time = elapsed_time or 0
        if self.device_state == DeviceState.Playing:
            return int(elapsed_time + diff)
        return int(elapsed_time)

    def _get_command_info(self, command):
        for cmd in self._state.supported_commands:
            if cmd.command == command:
                return cmd
        return None

    @property
    def shuffle(self):
        """If shuffle is enabled or not."""
        info = self._get_command_info(CommandInfo_pb2.ChangeShuffleMode)
        if info is None:
            return ShuffleState.Off
        if info.shuffleMode == protobuf.CommandInfo.Off:
            return ShuffleState.Off
        if info.shuffleMode == protobuf.CommandInfo.Albums:
            return ShuffleState.Albums

        return ShuffleState.Songs

    @property
    def repeat(self):
        """Repeat mode."""
        info = self._get_command_info(CommandInfo_pb2.ChangeRepeatMode)
        if info is None:
            return RepeatState.Off
        if info.repeatMode == protobuf.CommandInfo.One:
            return RepeatState.Track

        return RepeatState.All

    @property
    def hash(self):
        """Create a unique hash for what is currently playing."""
        return self._state.item_identifier or super().hash


class MrpMetadata(Metadata):
    """Implementation of API for retrieving metadata."""

    def __init__(self, protocol, psm, identifier):
        """Initialize a new MrpPlaying."""
        super().__init__(identifier)
        self.protocol = protocol
        self.psm = psm
        self.artwork_cache = Cache(limit=4)

    async def artwork(self):
        """Return artwork for what is currently playing (or None)."""
        identifier = self.artwork_id
        if not identifier:
            _LOGGER.debug('No artwork available')
            return None

        if identifier in self.artwork_cache:
            _LOGGER.debug('Retrieved artwork %s from cache', identifier)
            return self.artwork_cache.get(identifier)

        artwork = await self._fetch_artwork()
        if artwork:
            self.artwork_cache.put(identifier, artwork)
            return artwork

        return None

    async def _fetch_artwork(self):
        playing = self.psm.playing
        resp = await self.psm.protocol.send_and_receive(
            messages.playback_queue_request(playing.location))
        if not resp.HasField('type'):
            return None

        item = resp.inner().playbackQueue.contentItems[playing.location]
        return ArtworkInfo(item.artworkData, playing.metadata.artworkMIMEType)

    @property
    def artwork_id(self):
        """Return a unique identifier for current artwork."""
        metadata = self.psm.playing.metadata
        if metadata and metadata.artworkAvailable:
            if metadata.HasField('artworkIdentifier'):
                return metadata.artworkIdentifier
            if metadata.HasField('contentIdentifier'):
                return metadata.contentIdentifier
        return None

    async def playing(self):
        """Return what is currently playing."""
        return MrpPlaying(self.psm.playing)


class MrpPushUpdater(PushUpdater):
    """Implementation of API for handling push update from an Apple TV."""

    def __init__(self, loop, metadata, psm):
        """Initialize a new MrpPushUpdater instance."""
        super().__init__()
        self.loop = loop
        self.metadata = metadata
        self.psm = psm
        self.listener = None

    @property
    def active(self):
        """Return if push updater has been started."""
        return self.psm.listener == self

    def start(self, initial_delay=0):
        """Wait for push updates from device.

        Will throw NoAsyncListenerError if no listener has been set.
        """
        if self.listener is None:
            raise exceptions.NoAsyncListenerError()
        if self.active:
            return

        self.psm.listener = self

    def stop(self):
        """No longer forward updates to listener."""
        self.psm.listener = None

    async def state_updated(self):
        """State was updated for active player."""
        try:
            playstatus = await self.metadata.playing()
            self.loop.call_soon(
                self.listener.playstatus_update, self, playstatus)
        except Exception as ex:  # pylint: disable=broad-except
            _LOGGER.debug('Playstatus error occurred: %s', ex)
            self.loop.call_soon(self.listener.playstatus_error, self, ex)


class MrpAppleTV(AppleTV):
    """Implementation of API support for Apple TV."""

    # This is a container class so it's OK with many attributes
    # pylint: disable=too-many-instance-attributes
    def __init__(self, loop, session, config, airplay):
        """Initialize a new Apple TV."""
        super().__init__()

        self._session = session
        self._mrp_service = config.get_service(Protocol.MRP)

        self._connection = MrpConnection(
            config.address, self._mrp_service.port, loop, atv=self)
        self._srp = SRPAuthHandler()
        self._protocol = MrpProtocol(
            loop, self._connection, self._srp, self._mrp_service)
        self._psm = PlayerStateManager(self._protocol, loop)

        self._mrp_remote = MrpRemoteControl(loop, self._protocol)
        self._mrp_metadata = MrpMetadata(
            self._protocol, self._psm, config.identifier)
        self._mrp_push_updater = MrpPushUpdater(
            loop, self._mrp_metadata, self._psm)
        self._airplay = airplay

    async def connect(self):
        """Initiate connection to device.

        No need to call it yourself, it's done automatically.
        """
        await self._protocol.start()

    async def close(self):
        """Close connection and release allocated resources."""
        if net.is_custom_session(self._session):
            await self._session.close()
        self._protocol.stop()

    @property
    def service(self):
        """Return service used to connect to the Apple TV."""
        return self._mrp_service

    @property
    def remote_control(self):
        """Return API for controlling the Apple TV."""
        return self._mrp_remote

    @property
    def metadata(self):
        """Return API for retrieving metadata from Apple TV."""
        return self._mrp_metadata

    @property
    def push_updater(self):
        """Return API for handling push update from the Apple TV."""
        return self._mrp_push_updater

    @property
    def stream(self):
        """Return API for streaming media."""
        return self._airplay
