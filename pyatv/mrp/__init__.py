"""Implementation of the MediaRemoteTV Protocol used by ATV4 and later."""

import math
import logging
import asyncio
import datetime

from pyatv import exceptions, net
from pyatv.const import (
    Protocol, MediaType, DeviceState, RepeatState, ShuffleState, PowerState)
from pyatv.cache import Cache
from pyatv.mrp import (messages, protobuf)
from pyatv.mrp.srp import SRPAuthHandler
from pyatv.mrp.connection import MrpConnection
from pyatv.mrp.protocol import MrpProtocol
from pyatv.mrp.protobuf import CommandInfo_pb2
from pyatv.mrp.protobuf.SetStateMessage_pb2 import SetStateMessage as ssm
from pyatv.mrp.player_state import PlayerStateManager
from pyatv.interface import (AppleTV, RemoteControl, Metadata,
                             Playing, PushUpdater, ArtworkInfo, Power)


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


def _cocoa_to_timestamp(time):
    delta = datetime.datetime(2001, 1, 1) - datetime.datetime(1970, 1, 1)
    time_seconds = (datetime.timedelta(seconds=time) + delta).total_seconds()
    return datetime.datetime.fromtimestamp(time_seconds)


# pylint: disable=too-many-public-methods
class MrpRemoteControl(RemoteControl):
    """Implementation of API for controlling an Apple TV."""

    def __init__(self, loop, protocol):
        """Initialize a new MrpRemoteControl."""
        self.loop = loop
        self.protocol = protocol

    async def _press_key(self, key, hold=False):
        lookup = _KEY_LOOKUP.get(key)
        if not lookup:
            raise Exception('unsupported key: ' + key)

        await self.protocol.send_and_receive(
            messages.send_hid_event(lookup[0], lookup[1], True))

        if hold:
            await asyncio.sleep(lookup[2])

        await self.protocol.send_and_receive(
            messages.send_hid_event(lookup[0], lookup[1], False))

    async def _send_command(self, command):
        resp = await self.protocol.send_and_receive(messages.command(command))
        inner = resp.inner()

        if inner.errorCode != 0:
            raise exceptions.CommandError(
                "Command {0} failed: {1}, {2}".format(
                    command, inner.errorCode, inner.handlerReturnStatus))

    async def up(self):
        """Press key up."""
        await self._press_key('up')

    async def down(self):
        """Press key down."""
        await self._press_key('down')

    async def left(self):
        """Press key left."""
        await self._press_key('left')

    async def right(self):
        """Press key right."""
        await self._press_key('right')

    async def play(self):
        """Press key play."""
        await self._send_command(CommandInfo_pb2.Play)

    async def pause(self):
        """Press key play."""
        await self._send_command(CommandInfo_pb2.Pause)

    async def stop(self):
        """Press key stop."""
        await self._send_command(CommandInfo_pb2.Stop)

    async def next(self):
        """Press key next."""
        await self._send_command(CommandInfo_pb2.NextTrack)

    async def previous(self):
        """Press key previous."""
        await self._send_command(CommandInfo_pb2.PreviousTrack)

    async def select(self):
        """Press key select."""
        await self._press_key('select')

    async def menu(self):
        """Press key menu."""
        await self._press_key('menu')

    async def volume_up(self):
        """Press key volume up."""
        await self._press_key('volume_up')

    async def volume_down(self):
        """Press key volume down."""
        await self._press_key('volume_down')

    async def home(self):
        """Press key home."""
        await self._press_key('home')

    async def home_hold(self):
        """Hold key home."""
        await self._press_key('home', hold=True)

    async def top_menu(self):
        """Go to main menu (long press menu)."""
        await self._press_key('topmenu')

    async def suspend(self):
        """Suspend the device."""
        await self._press_key('suspend')

    async def wakeup(self):
        """Wake up the device."""
        await self._press_key('wakeup')

    async def set_position(self, pos):
        """Seek in the current playing media."""
        await self.protocol.send_and_receive(
            messages.seek_to_position(pos))

    async def set_shuffle(self, shuffle_state):
        """Change shuffle mode to on or off."""
        await self.protocol.send_and_receive(
            messages.shuffle(shuffle_state))

    async def set_repeat(self, repeat_state):
        """Change repeat state."""
        await self.protocol.send_and_receive(
            messages.repeat(repeat_state))


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
    def device_state(self):
        """Device state, e.g. playing or paused."""
        return {
            None: DeviceState.Idle,
            ssm.Playing: DeviceState.Playing,
            ssm.Paused: DeviceState.Paused,
            ssm.Stopped: DeviceState.Stopped,
            ssm.Interrupted: DeviceState.Loading,
            ssm.Seeking: DeviceState.Seeking
            }.get(self._state.playback_state,
                  DeviceState.Paused)

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
        elapsed_timestamp = self._state.metadata_field('elapsedTimeTimestamp')

        # If we don't have reference time, we can't do anything
        if not elapsed_timestamp:
            return None

        elapsed_time = self._state.metadata_field('elapsedTime') or 0
        diff = (datetime.datetime.now() - _cocoa_to_timestamp(
            elapsed_timestamp)).total_seconds()

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


class MrpPower(Power):
    """Implementation of API for retrieving a power state from an Apple TV."""

    def __init__(self, loop, protocol, remote):
        """Initialize a new MrpPower instance."""
        super().__init__()
        self.loop = loop
        self.protocol = protocol
        self.remote = remote
        self.device_info = None
        self.__listener = None

        self.protocol.add_listener(
            self._update_power_state,
            protobuf.DEVICE_INFO_UPDATE_MESSAGE)

    def _get_current_power_state(self):
        latest_device_info = self.device_info or self.protocol.device_info
        return self._get_power_state(latest_device_info)

    @property
    def power_state(self):
        """Return device power state."""
        currect_power_state = self._get_current_power_state()
        return currect_power_state

    async def turn_on(self):
        """Turn device on."""
        await self.protocol.send_and_receive(messages.wake_device())

    async def turn_off(self):
        """Turn device off."""
        await self.remote.home_hold()
        await self.remote.select()

    async def _update_power_state(self, message, _):
        old_state = self.power_state
        new_state = self._get_power_state(message)
        self.device_info = message

        if new_state != old_state:
            _LOGGER.debug(
                'Power state changed from %s to %s',
                old_state, new_state)
            if self.listener:
                self.loop.call_soon(
                    self.listener.powerstate_update, old_state, new_state)

    @staticmethod
    def _get_power_state(device_info):
        logical_device_count = device_info.inner().logicalDeviceCount
        if logical_device_count >= 1:
            return PowerState.On
        if logical_device_count == 0:
            return PowerState.Off
        return PowerState.Unknown


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
        self._config = config
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
        self._mrp_power = MrpPower(
            loop, self._protocol, self._mrp_remote)
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
    def device_info(self):
        """Return API for device information."""
        return self._config.device_info

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

    @property
    def power(self):
        """Return API for streaming media."""
        return self._mrp_power
