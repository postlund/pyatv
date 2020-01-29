"""Fake MRP Apple TV for tests."""

import asyncio
import logging
import struct
from datetime import datetime

from pyatv import const
from pyatv.mrp import (chacha20, messages, protobuf, variant)
from pyatv.mrp.protobuf import CommandInfo_pb2 as cmd
from pyatv.mrp.protobuf import SetStateMessage as ssm
from tests.airplay.fake_airplay_device import (
    FakeAirPlayDevice, AirPlayUseCases)
from tests.mrp.mrp_server_auth import MrpServerAuth

_LOGGER = logging.getLogger(__name__)

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
}

_COMMAND_LOOKUP = {
    cmd.Play: 'play',
    cmd.Pause: 'pause',
    cmd.Stop: 'stop',
    cmd.NextTrack: 'nextitem',
    cmd.PreviousTrack: 'previtem',
}

_REPEAT_LOOKUP = {
    const.RepeatState.Track: protobuf.CommandInfo.One,
    const.RepeatState.All: protobuf.CommandInfo.All,
}

_SHUFFLE_LOOKUP = {
    const.ShuffleState.Off: protobuf.CommandInfo.Off,
    const.ShuffleState.Albums: protobuf.CommandInfo.Albums,
    const.ShuffleState.Songs: protobuf.CommandInfo.Songs,
}

_COCOA_BASE = (datetime(1970, 1, 1) - datetime(2001, 1, 1)).total_seconds()


DEVICE_NAME = 'Fake MRP ATV'
PLAYER_IDENTIFIER = 'com.github.postlund.pyatv'


def _convert_key_press(use_page, usage):
    for name, codes in _KEY_LOOKUP.items():
        if codes[0] == use_page and codes[1] == usage:
            return name
    raise Exception(
        'unsupported key: use_page={0}, usage={1}'.format(
            use_page, usage))


def _fill_item(item, metadata):
    if metadata.identifier:
        item.identifier = metadata.identifier

    md = item.metadata
    if metadata.artist:
        md.trackArtistName = metadata.artist
    if metadata.album:
        md.albumName = metadata.album
    if metadata.title:
        md.title = metadata.title
    if metadata.genre:
        md.genre = metadata.genre
    if metadata.total_time:
        md.duration = metadata.total_time
    if metadata.position:
        md.elapsedTime = metadata.position
    if metadata.playback_rate:
        md.playbackRate = metadata.playback_rate
    if metadata.media_type:
        md.mediaType = metadata.media_type
    if metadata.artwork_mimetype:
        md.artworkAvailable = True
        md.artworkMIMEType = metadata.artwork_mimetype
        md.artworkIdentifier = metadata.artwork_identifier


def _set_state_message(metadata, identifier):
    # Most things are hardcoded here for simplicity. Will change that
    # as time goes by and more dynamic content is needed.
    set_state = messages.create(protobuf.SET_STATE_MESSAGE)
    inner = set_state.inner()
    inner.playbackState = metadata.playback_state
    inner.displayName = 'Fake Player'
    inner.playbackStateTimestamp = _COCOA_BASE

    if metadata.repeat and metadata.repeat != const.RepeatState.Off:
        cmd = inner.supportedCommands.supportedCommands.add()
        cmd.command = protobuf.CommandInfo_pb2.ChangeRepeatMode
        cmd.repeatMode = _REPEAT_LOOKUP[metadata.repeat]

    if metadata.shuffle:
        cmd = inner.supportedCommands.supportedCommands.add()
        cmd.command = protobuf.CommandInfo_pb2.ChangeShuffleMode
        cmd.shuffleMode = metadata.shuffle

    queue = inner.playbackQueue
    queue.location = 0
    _fill_item(queue.contentItems.add(), metadata)

    client = inner.playerPath.client
    client.processIdentifier = 123
    client.bundleIdentifier = identifier
    return set_state


class PlayingMetadata:

    def __init__(self, **kwargs):
        """Initialize a new PlayingMetadata."""
        self.identifier = kwargs.get('identifier')
        self.playback_state = kwargs.get('playback_state')
        self.title = kwargs.get('title')
        self.artist = kwargs.get('artist')
        self.album = kwargs.get('album')
        self.genre = kwargs.get('genre')
        self.total_time = kwargs.get('total_time')
        self.position = kwargs.get('position')
        self.repeat = kwargs.get('repeat')
        self.shuffle = _SHUFFLE_LOOKUP.get(kwargs.get('shuffle'))
        self.media_type = kwargs.get('media_type')
        self.playback_rate = kwargs.get('playback_rate')
        self.artwork = None
        self.artwork_mimetype = None


class FakeAppleTV(FakeAirPlayDevice, MrpServerAuth, asyncio.Protocol):
    """Implementation of a fake MRP Apple TV."""

    def __init__(self, testcase, loop):
        FakeAirPlayDevice.__init__(self, testcase)
        MrpServerAuth.__init__(self, self, DEVICE_NAME)
        self.loop = loop
        self.app.on_startup.append(self.start)
        self.outstanding_keypresses = set()  # Pressed but not released
        self.last_button_pressed = None
        self.connection_state = None
        self.states = {}
        self.active_player = None
        self.has_authenticated = False

        self.server = None
        self.buffer = b''
        self.chacha = None
        self.transport = None

    async def start(self, app):
        coro = self.loop.create_server(lambda: self, '127.0.0.1')
        self.server = await self.loop.create_task(coro)
        _LOGGER.info('Started MRP server at port %d', self.port)

    @property
    def port(self):
        return self.server.sockets[0].getsockname()[1]

    def connection_made(self, transport):
        self.transport = transport

    def enable_encryption(self, input_key, output_key):
        """Enable encryption with specified keys."""
        self.chacha = chacha20.Chacha20Cipher(
            input_key, output_key)
        self.has_authenticated = True

    def send(self, message):
        data = message.SerializeToString()
        if self.chacha:
            data = self.chacha.encrypt(data)

        length = variant.write_variant(len(data))
        self.transport.write(length + data)

    def update_state(self, identifier):
        state = self.states[identifier]
        self.send(_set_state_message(state, identifier))

    def set_player_state(self, identifier, state):
        self.states[identifier] = state
        self.update_state(identifier)

    def get_player_state(self, identifier):
        return self.states[identifier]

    def set_active_player(self, identifier):
        if identifier is not None and identifier not in self.states:
            raise Exception('invalid player: %s', identifier)

        self.active_player = identifier
        now_playing = messages.create(
            protobuf.SET_NOW_PLAYING_CLIENT_MESSAGE)
        client = now_playing.inner().client
        if identifier:
            client.bundleIdentifier = identifier
        self.send(now_playing)

    def item_update(self, metadata, identifier):
        msg = messages.create(protobuf.UPDATE_CONTENT_ITEM_MESSAGE)
        inner = msg.inner()

        _fill_item(inner.contentItems.add(), metadata)

        client = inner.playerPath.client
        client.processIdentifier = 123
        client.bundleIdentifier = identifier

        self.send(msg)

    def data_received(self, data):
        self.buffer += data

        while self.buffer:
            length, raw = variant.read_variant(self.buffer)
            if len(raw) < length:
                return

            data = raw[:length]
            self.buffer = raw[length:]
            if self.chacha:
                data = self.chacha.decrypt(data)

            parsed = protobuf.ProtocolMessage()
            parsed.ParseFromString(data)
            _LOGGER.info('Incoming message: %s', parsed)

            try:
                name = parsed.Type.Name(
                    parsed.type).lower().replace('_message', '')

                _LOGGER.debug('Received %s message', name)
                getattr(self, 'handle_' + name)(parsed, parsed.inner())
            except AttributeError:
                _LOGGER.exception('No message handler for ' + str(parsed))
            except Exception:
                _LOGGER.exception('Error while dispatching message')

    def handle_device_info(self, message, inner):
        resp = messages.device_information(DEVICE_NAME, '1234')
        resp.identifier = message.identifier
        self.send(resp)

    def handle_set_connection_state(self, message, inner):
        _LOGGER.debug('Changed connection state to %d', inner.state)
        self.connection_state = inner.state

    def handle_client_updates_config(self, message, inner):
        pass

    def handle_get_keyboard_session(self, message, inner):
        # This message has a lot more fields, but pyatv currently
        # not use them so ignore for now
        self.send(messages.create(
            protobuf.KEYBOARD_MESSAGE, identifier=message.identifier))

    def handle_send_hid_event(self, message, inner):
        # These corresponds to the bytes mapping to pressed key (see
        # send_hid_event in pyatv/mrp/messages.py)
        start = inner.hidEventData[43:49]
        use_page, usage, down_press = struct.unpack('>HHH', start)

        if down_press == 1:
            self.outstanding_keypresses.add((use_page, usage))
        elif down_press == 0:
            if (use_page, usage) in self.outstanding_keypresses:
                self.last_button_pressed = _convert_key_press(use_page, usage)
                self.outstanding_keypresses.remove((use_page, usage))
                _LOGGER.debug('Pressed button: %s', self.last_button_pressed)
            else:
                _LOGGER.error('Missing key down for %d,%d', use_page, usage)
        else:
            _LOGGER.error('Invalid key press state: %d', down_press)

    def handle_send_command(self, message, inner):
        button = _COMMAND_LOOKUP.get(inner.command)
        if button:
            self.last_button_pressed = button
            _LOGGER.debug('Pressed button: %s', self.last_button_pressed)
        elif inner.command == cmd.ChangeRepeatMode:
            state = self.get_player_state(self.active_player)
            repeatMode = inner.options.repeatMode
            if repeatMode == protobuf.CommandInfo.One:
                state.repeat = const.RepeatState.Track
            elif repeatMode == protobuf.CommandInfo.All:
                state.repeat = const.RepeatState.All
            else:
                state.repeat = const.RepeatState.Off
            self.update_state(self.active_player)
            _LOGGER.debug('Change repeat state to %s', state.repeat)
        elif inner.command == cmd.ChangeShuffleMode:
            state = self.get_player_state(self.active_player)
            state.shuffle = inner.options.shuffleMode
            self.update_state(self.active_player)
            _LOGGER.debug('Change shuffle state to %s', state.shuffle)
        elif inner.command == cmd.SeekToPlaybackPosition:
            state = self.get_player_state(self.active_player)
            state.position = inner.options.playbackPosition
            self.update_state(self.active_player)
            _LOGGER.debug('Seek to position: %d', state.position)
        else:
            _LOGGER.warning(
                'Unhandled button press: %s', message.inner().command)

    def handle_playback_queue_request(self, message, inner):
        setstate = messages.create(
            protobuf.SET_STATE_MESSAGE, identifier=message.identifier)
        queue = setstate.inner().playbackQueue
        queue.location = 0
        item = queue.contentItems.add()
        item.artworkData = self.states[self.active_player].artwork
        item.artworkDataWidth = 456
        item.artworkDataHeight = 789
        self.send(setstate)


class AppleTVUseCases(AirPlayUseCases):
    """Wrapper for altering behavior of a FakeMrpAppleTV instance."""

    def __init__(self, fake_apple_tv):
        """Initialize a new AppleTVUseCases."""
        self.device = fake_apple_tv

    def change_artwork(self, artwork, mimetype, identifier='artwork'):
        """Call this method to change artwork response."""
        metadata = self.device.get_player_state(PLAYER_IDENTIFIER)
        metadata.artwork = artwork
        metadata.artwork_mimetype = mimetype
        metadata.artwork_identifier = identifier
        self.device.update_state(PLAYER_IDENTIFIER)

    def change_metadata(self, **kwargs):
        """Change metadata for item via ContentItemUpdate."""
        metadata = self.device.get_player_state(PLAYER_IDENTIFIER)

        # Update saved metadata
        for key, value in kwargs.items():
            setattr(metadata, key, value)

        # Create a temporary metadata instance with requested parameters
        change = PlayingMetadata(**kwargs)
        self.device.item_update(change, PLAYER_IDENTIFIER)

    def nothing_playing(self):
        """Call this method to put device in idle state."""
        self.device.set_active_player(None)

    def example_video(self, **kwargs):
        """Play some example video."""
        self.video_playing(paused=True, title='dummy',
                           total_time=123, position=3, **kwargs)

    def video_playing(self, paused, title, total_time, position, **kwargs):
        """Call this method to change what is currently plaing to video."""
        metadata = PlayingMetadata(
            playback_state=ssm.Paused if paused else ssm.Playing,
            title=title, total_time=total_time,
            position=position, media_type=protobuf.ContentItemMetadata.Video,
            **kwargs)
        self.device.set_player_state(PLAYER_IDENTIFIER, metadata)
        self.device.set_active_player(PLAYER_IDENTIFIER)

    def music_playing(self, paused, artist, album, title, genre,
                      total_time, position, **kwargs):
        """Call this method to change what is currently plaing to music."""
        metadata = PlayingMetadata(
            playback_state=ssm.Paused if paused else ssm.Playing,
            artist=artist, album=album, title=title, genre=genre,
            total_time=total_time, position=position,
            media_type=protobuf.ContentItemMetadata.Music,
            **kwargs)
        self.device.set_player_state(PLAYER_IDENTIFIER, metadata)
        self.device.set_active_player(PLAYER_IDENTIFIER)

    def media_is_loading(self):
        """Call this method to put device in a loading state."""
        metadata = PlayingMetadata(playback_state=ssm.Interrupted)
        self.device.set_player_state(PLAYER_IDENTIFIER, metadata)
        self.device.set_active_player(PLAYER_IDENTIFIER)
