"""Implementation of the MediaRemoteTV Protocol used by ATV4 and later."""

import logging
import asyncio
from datetime import datetime

from pyatv import (const, exceptions)
from pyatv.mrp import (messages, protobuf)
from pyatv.mrp.srp import SRPAuthHandler
from pyatv.mrp.connection import MrpConnection
from pyatv.mrp.protocol import MrpProtocol
from pyatv.mrp.protobuf import CommandInfo_pb2, SetStateMessage_pb2
from pyatv.mrp.player_state import PlayerStateManager
from pyatv.interface import (AppleTV, RemoteControl, Metadata,
                             Playing, PushUpdater)


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
    'top_menu': [12, 0x60, 0],
    'home': [12, 0x40, 0],
    'home_hold': [12, 0x40, 1],
    'suspend': [1, 0x82, 0],
    'volume_up': [12, 0xE9, 0],
    'volume_down': [12, 0xEA, 0],

    # 'mic': [12, 0x04, 0],  # Siri
}


class MrpRemoteControl(RemoteControl):
    """Implementation of API for controlling an Apple TV."""

    def __init__(self, loop, protocol):
        """Initialize a new MrpRemoteControl."""
        self.loop = loop
        self.protocol = protocol

    async def _press_key(self, key):
        lookup = _KEY_LOOKUP.get(key, None)
        if lookup:
            await self.protocol.send(
                messages.send_hid_event(lookup[0], lookup[1], True))
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
        return self._press_key('home_hold')

    def top_menu(self):
        """Go to main menu (long press menu)."""
        return self._press_key('top_menu')

    def suspend(self):
        """Suspend the device."""
        return self._press_key('suspend')

    def set_position(self, pos):
        """Seek in the current playing media."""
        return self.protocol.send(messages.seek_to_position(pos))

    def set_shuffle(self, is_on):
        """Change shuffle mode to on or off."""
        return self.protocol.send(messages.shuffle(is_on))

    def set_repeat(self, repeat_mode):
        """Change repeat mode."""
        # TODO: extract to convert module
        if int(repeat_mode) == const.REPEAT_STATE_OFF:
            state = 1
        elif int(repeat_mode) == const.REPEAT_STATE_ALL:
            state = 2
        elif int(repeat_mode) == const.REPEAT_STATE_TRACK:
            state = 3
        else:
            raise ValueError('Invalid repeat mode: ' + str(repeat_mode))

        return self.protocol.send(messages.repeat(state))


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
            cim = protobuf.ContentItemMetadata_pb2.ContentItemMetadata
            if media_type == cim.Audio:
                return const.MEDIA_TYPE_MUSIC
            if media_type == cim.Video:
                return const.MEDIA_TYPE_VIDEO

        return const.MEDIA_TYPE_UNKNOWN

    @property
    def play_state(self):
        """Play state, e.g. playing or paused."""
        if self._state is None:
            return const.PLAY_STATE_IDLE

        state = self._state.playback_state
        ssm = SetStateMessage_pb2.SetStateMessage
        if state == ssm.Playing:
            return const.PLAY_STATE_PLAYING
        if state == ssm.Paused:
            return const.PLAY_STATE_PAUSED
        if state == ssm.Stopped:
            return const.PLAY_STATE_STOPPED
        if state == ssm.Interrupted:
            return const.PLAY_STATE_LOADING
        # if state == SetStateMessage_pb2.Seeking
        #    return XXX

        return const.PLAY_STATE_PAUSED

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
        return None if duration is None else int(duration)

    @property
    def position(self):
        """Position in the playing media (seconds)."""
        elapsed_time = self._state.metadata_field('elapsedTime')
        if elapsed_time:
            diff = (datetime.now() - self._state.timestamp).total_seconds()
            if self.play_state == const.PLAY_STATE_PLAYING:
                return int(elapsed_time + diff)
            return int(elapsed_time)
        return None

    def _get_command_info(self, command):
        for cmd in self._state.supported_commands:
            if cmd.command == command:
                return cmd
        return None

    @property
    def shuffle(self):
        """If shuffle is enabled or not."""
        info = self._get_command_info(CommandInfo_pb2.ChangeShuffleMode)
        return None if info is None else info.shuffleMode

    @property
    def repeat(self):
        """Repeat mode."""
        info = self._get_command_info(CommandInfo_pb2.ChangeRepeatMode)
        return None if info is None else info.repeatMode


class MrpMetadata(Metadata):
    """Implementation of API for retrieving metadata."""

    def __init__(self, psm, identifier):
        """Initialize a new MrpPlaying."""
        super().__init__(identifier)
        self.psm = psm

    async def artwork(self):
        """Return artwork for what is currently playing (or None)."""
        raise exceptions.NotSupportedError

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

    def start(self, initial_delay=0):
        """Wait for push updates from device.

        Will throw NoAsyncListenerError if no listner has been set.
        """
        if self.listener is None:
            raise exceptions.NoAsyncListenerError

        self.psm.listener = self

    def stop(self):
        """No longer wait for push updates."""
        self.psm.listener = None

    async def state_updated(self):
        """State was updated for active player."""
        playstatus = await self.metadata.playing()
        self.loop.call_soon(
            self.listener.playstatus_update, self, playstatus)


class MrpAppleTV(AppleTV):
    """Implementation of API support for Apple TV."""

    # This is a container class so it's OK with many attributes
    # pylint: disable=too-many-instance-attributes
    def __init__(self, loop, session, config, airplay):
        """Initialize a new Apple TV."""
        super().__init__()

        self._session = session
        self._mrp_service = config.get_service(const.PROTOCOL_MRP)

        self._connection = MrpConnection(
            config.address, self._mrp_service.port, loop)
        self._srp = SRPAuthHandler()
        self._protocol = MrpProtocol(
            loop, self._connection, self._srp, self._mrp_service)
        self._psm = PlayerStateManager(self._protocol, loop)

        self._mrp_remote = MrpRemoteControl(loop, self._protocol)
        self._mrp_metadata = MrpMetadata(self._psm, config.identifier)
        self._mrp_push_updater = MrpPushUpdater(
            loop, self._mrp_metadata, self._psm)
        self._airplay = airplay

    async def connect(self):
        """Initiate connection to device.

        Not needed as it is performed automatically.
        """
        await self._protocol.start()

    async def close(self):
        """Close connection and release allocated resources."""
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
    def airplay(self):
        """Return API for working with AirPlay."""
        return self._airplay
