"""Fake MRP Apple TV for tests."""

import asyncio
import logging
import struct
from datetime import datetime
from typing import Dict, Tuple, Optional

from pyatv import const
from pyatv.support import log_protobuf
from pyatv.mrp import chacha20, messages, protobuf, variant
from pyatv.mrp.protobuf import CommandInfo_pb2 as cmd
from pyatv.mrp.protobuf import SetStateMessage as ssm
from pyatv.mrp.protobuf import SendCommandResultMessage as scr
from pyatv.mrp.server_auth import MrpServerAuth

from tests.utils import stub_sleep

_LOGGER = logging.getLogger(__name__)

_KEY_LOOKUP = {
    # (use_page, usage): button
    (1, 0x8C): "up",
    (1, 0x8D): "down",
    (1, 0x8B): "left",
    (1, 0x8A): "right",
    (12, 0xB7): "stop",
    (12, 0xB5): "next",
    (12, 0xB6): "previous",
    (1, 0x89): "select",
    (1, 0x86): "menu",
    (12, 0x60): "top_menu",
    (12, 0x40): "home",
    (1, 0x82): "suspend",
    (1, 0x83): "wakeup",
    (12, 0xE9): "volumeup",
    (12, 0xEA): "volumedown",
}  # Dict[Tuple(int, int), str]

_COMMAND_LOOKUP = {
    cmd.Play: "play",
    cmd.TogglePlayPause: "playpause",
    cmd.Pause: "pause",
    cmd.Stop: "stop",
    cmd.NextTrack: "nextitem",
    cmd.PreviousTrack: "previtem",
}

_REPEAT_LOOKUP = {
    const.RepeatState.Off: protobuf.RepeatMode.Off,
    const.RepeatState.Track: protobuf.RepeatMode.One,
    const.RepeatState.All: protobuf.RepeatMode.All,
}

_SHUFFLE_LOOKUP = {
    const.ShuffleState.Off: protobuf.ShuffleMode.Off,
    const.ShuffleState.Albums: protobuf.ShuffleMode.Albums,
    const.ShuffleState.Songs: protobuf.ShuffleMode.Songs,
}

_COCOA_BASE = (datetime(1970, 1, 1) - datetime(2001, 1, 1)).total_seconds()


APP_NAME = "Test app"
DEVICE_NAME = "Fake MRP ATV"
PLAYER_IDENTIFIER = "com.github.postlund.pyatv"


def _fill_item(item, metadata):
    if metadata.identifier:
        item.identifier = metadata.identifier

    md = item.metadata
    md.elapsedTimeTimestamp = _COCOA_BASE
    if metadata.artist:
        md.trackArtistName = metadata.artist
    if metadata.album:
        md.albumName = metadata.album
    if metadata.title:
        md.title = metadata.title
    if metadata.genre:
        md.genre = metadata.genre
    if metadata.total_time is not None:
        md.duration = metadata.total_time
    if metadata.position is not None:
        md.elapsedTime = metadata.position
    if metadata.playback_rate is not None:
        md.playbackRate = metadata.playback_rate
    if metadata.media_type:
        md.mediaType = metadata.media_type
    if metadata.artwork_mimetype:
        md.artworkAvailable = True
        md.artworkMIMEType = metadata.artwork_mimetype
        if metadata.artwork_identifier:
            md.artworkIdentifier = metadata.artwork_identifier


def _set_state_message(metadata, identifier):
    # Most things are hardcoded here for simplicity. Will change that
    # as time goes by and more dynamic content is needed.
    set_state = messages.create(protobuf.SET_STATE_MESSAGE)
    inner = set_state.inner()
    inner.playbackState = metadata.playback_state
    inner.displayName = "Fake Player"

    if metadata.supported_commands:
        for command in metadata.supported_commands:
            item = inner.supportedCommands.supportedCommands.add()
            item.command = command
            item.enabled = True

            if command in [
                protobuf.CommandInfo_pb2.SkipForward,
                protobuf.CommandInfo_pb2.SkipBackward,
            ]:
                if metadata.skip_time is not None:
                    item.preferredIntervals.append(metadata.skip_time)

    if metadata.repeat:
        cmd = inner.supportedCommands.supportedCommands.add()
        cmd.command = protobuf.CommandInfo_pb2.ChangeRepeatMode
        cmd.repeatMode = _REPEAT_LOOKUP[metadata.repeat]

    if metadata.shuffle:
        cmd = inner.supportedCommands.supportedCommands.add()
        cmd.command = protobuf.CommandInfo_pb2.ChangeShuffleMode
        cmd.shuffleMode = _SHUFFLE_LOOKUP.get(metadata.shuffle)

    queue = inner.playbackQueue
    queue.location = 0
    _fill_item(queue.contentItems.add(), metadata)

    client = inner.playerPath.client
    client.processIdentifier = 123
    client.bundleIdentifier = identifier
    client.displayName = APP_NAME
    return set_state


class PlayingState:
    def __init__(self, **kwargs):
        """Initialize a new PlayingState."""
        self.identifier = kwargs.get("identifier")
        self.playback_state = kwargs.get("playback_state")
        self.title = kwargs.get("title")
        self.artist = kwargs.get("artist")
        self.album = kwargs.get("album")
        self.genre = kwargs.get("genre")
        self.total_time = kwargs.get("total_time")
        self.position = kwargs.get("position")
        self.repeat = kwargs.get("repeat")
        self.shuffle = kwargs.get("shuffle")
        self.media_type = kwargs.get("media_type")
        self.playback_rate = kwargs.get("playback_rate")
        self.supported_commands = kwargs.get("supported_commands")
        self.artwork = kwargs.get("artwork")
        self.artwork_mimetype = kwargs.get("artwork_mimetype")
        self.artwork_width = kwargs.get("artwork_width")
        self.artwork_height = kwargs.get("artwork_height")
        self.skip_time = kwargs.get("skip_time")


class FakeMrpState:
    def __init__(self):
        """State of a fake MRP device."""
        self.clients = []
        self.outstanding_keypresses = {}  # Dict[Tuple[int, int], flot]
        self.last_button_pressed: Optional[str] = None
        self.last_button_action: Optional[const.InputAction] = None
        self.connection_state = None
        self.states = {}
        self.active_player = None
        self.powered_on = True
        self.has_authenticated = False

    def _send(self, msg):
        for client in self.clients:
            client.send(msg)

    # This is a hack for now (if anyone has paired, OK...)
    @property
    def has_paired(self):
        return any([client.has_paired for client in self.clients])

    def update_state(self, identifier):
        state = self.states[identifier]
        self._send(_set_state_message(state, identifier))

    def set_player_state(self, identifier, state):
        self.states[identifier] = state
        self.update_state(identifier)

    def get_player_state(self, identifier):
        return self.states.get(identifier)

    def set_active_player(self, identifier):
        if identifier is not None and identifier not in self.states:
            raise Exception("invalid player: %s", identifier)

        self.active_player = identifier
        now_playing = messages.create(protobuf.SET_NOW_PLAYING_CLIENT_MESSAGE)
        client = now_playing.inner().client
        if identifier:
            client.bundleIdentifier = identifier
        self._send(now_playing)

    def item_update(self, metadata, identifier):
        msg = messages.create(protobuf.UPDATE_CONTENT_ITEM_MESSAGE)
        inner = msg.inner()

        _fill_item(inner.contentItems.add(), metadata)

        client = inner.playerPath.client
        client.processIdentifier = 123
        client.bundleIdentifier = identifier

        state = self.get_player_state(identifier)
        for var, value in vars(metadata).items():
            if value:
                setattr(state, var, value)

        self._send(msg)

    def update_client(self, display_name, identifier):
        msg = messages.create(protobuf.UPDATE_CLIENT_MESSAGE)
        client = msg.inner().client
        client.bundleIdentifier = identifier
        if display_name is not None:
            client.displayName = display_name
        self._send(msg)

    def volume_control(self, available):
        msg = messages.create(protobuf.VOLUME_CONTROL_AVAILABILITY_MESSAGE)
        msg.inner().volumeControlAvailable = available
        self._send(msg)


class FakeMrpServiceFactory:
    def __init__(self, state, app, loop):
        self.state = state
        self.app = app
        self.loop = loop
        self.server = None

    async def start(self, start_web_server: bool):
        coro = self.loop.create_server(
            lambda: FakeMrpService(self.state, self.app, self.loop), "0.0.0.0"
        )
        self.server = await self.loop.create_task(coro)
        _LOGGER.info("Started MRP server at port %d", self.port)

    async def cleanup(self):
        if self.server:
            self.server.close()

    @property
    def port(self):
        return self.server.sockets[0].getsockname()[1]


class FakeMrpService(MrpServerAuth, asyncio.Protocol):
    """Implementation of a fake MRP Apple TV."""

    def __init__(self, state, app, loop):
        MrpServerAuth.__init__(self, self, DEVICE_NAME)
        self.state = state
        self.state.clients.append(self)
        self.app = app
        self.loop = loop

        self.buffer = b""
        self.chacha = None
        self.transport = None

    def connection_made(self, transport):
        _LOGGER.debug("Client connected")
        self.transport = transport

    def connection_lost(self, exc):
        _LOGGER.debug("Client disconnected")
        self.transport = None
        self.state.clients.remove(self)

    def enable_encryption(self, input_key, output_key):
        """Enable encryption with specified keys."""
        self.chacha = chacha20.Chacha20Cipher(input_key, output_key)
        self.state.has_authenticated = True

    def send(self, message):
        if not self.transport:
            return

        data = message.SerializeToString()
        if self.chacha:
            data = self.chacha.encrypt(data)

        length = variant.write_variant(len(data))
        self.transport.write(length + data)
        log_protobuf(_LOGGER, ">> Send: Protobuf", message)

    def _send_device_info(self, identifier=None, update=False):
        resp = messages.device_information(DEVICE_NAME, "1234", update=update)
        if identifier:
            resp.identifier = identifier
        resp.inner().logicalDeviceCount = 1 if self.state.powered_on else 0
        self.send(resp)

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
            log_protobuf(_LOGGER, "<< Receive: Protobuf", parsed)

            try:
                name = parsed.Type.Name(parsed.type).lower().replace("_message", "")

                _LOGGER.debug("Received %s message", name)
                getattr(self, "handle_" + name)(parsed, parsed.inner())
            except AttributeError:
                _LOGGER.exception("No message handler for " + str(parsed))
            except Exception:
                _LOGGER.exception("Error while dispatching message")

    def handle_device_info(self, message, inner):
        self._send_device_info(update=False, identifier=message.identifier)

    def handle_set_connection_state(self, message, inner):
        _LOGGER.debug("Changed connection state to %d", inner.state)
        self.state.connection_state = inner.state

    def handle_client_updates_config(self, message, inner):
        for identifier, metadata in self.state.states.items():
            self.send(_set_state_message(metadata, identifier))

        # Trigger sending of SetNowPlayingClientMessage
        if self.state.active_player:
            self.state.set_active_player(self.state.active_player)

        if message.identifier is not None:
            self.send(messages.create(0, identifier=message.identifier))

    def handle_get_keyboard_session(self, message, inner):
        # This message has a lot more fields, but pyatv currently
        # not use them so ignore for now
        self.send(
            messages.create(protobuf.KEYBOARD_MESSAGE, identifier=message.identifier)
        )

    def handle_send_hid_event(self, message, inner):
        outstanding = self.state.outstanding_keypresses

        # These corresponds to the bytes mapping to pressed key (see
        # send_hid_event in pyatv/mrp/messages.py)
        start = inner.hidEventData[43:49]
        use_page, usage, down_press = struct.unpack(">HHH", start)

        if down_press == 1:
            outstanding[(use_page, usage)] = stub_sleep()
            self.send(messages.create(0, identifier=message.identifier))
        elif down_press == 0:
            if (use_page, usage) in outstanding:
                pressed_key = _KEY_LOOKUP.get((use_page, usage))
                if not pressed_key:
                    raise Exception(
                        f"unsupported key: use_page={use_page}, usage={usage}"
                    )
                if pressed_key == "select" and self.state.last_button_pressed == "home":
                    self.state.powered_on = False
                    self._send_device_info(update=True)

                time_diff = stub_sleep() - outstanding[(use_page, usage)]
                if time_diff > 0.5:
                    self.state.last_button_action = const.InputAction.Hold
                elif self.state.last_button_pressed == pressed_key:
                    # NB: Will report double tap for >= 3 clicks (fix when needed)
                    self.state.last_button_action = const.InputAction.DoubleTap
                else:
                    self.state.last_button_action = const.InputAction.SingleTap

                self.state.last_button_pressed = pressed_key
                del outstanding[(use_page, usage)]
                _LOGGER.debug("Pressed button: %s", self.state.last_button_pressed)
                self.send(messages.create(0, identifier=message.identifier))
            else:
                _LOGGER.error("Missing key down for %d,%d", use_page, usage)
        else:
            _LOGGER.error("Invalid key press state: %d", down_press)

    def handle_send_command(self, message, inner):
        state = self.state.get_player_state(self.state.active_player)
        button = _COMMAND_LOOKUP.get(inner.command)
        if button:
            self.state.last_button_pressed = button
            _LOGGER.debug("Pressed button: %s", self.state.last_button_pressed)
        elif inner.command == cmd.ChangeRepeatMode:
            state.repeat = {
                protobuf.RepeatMode.Off: const.RepeatState.Off,
                protobuf.RepeatMode.One: const.RepeatState.Track,
                protobuf.RepeatMode.All: const.RepeatState.All,
            }.get(inner.options.repeatMode, const.RepeatState.Off)
            self.state.update_state(self.state.active_player)
            _LOGGER.debug("Change repeat state to %s", state.repeat)
        elif inner.command == cmd.ChangeShuffleMode:
            state.shuffle = {
                protobuf.ShuffleMode.Off: const.ShuffleState.Off,
                protobuf.ShuffleMode.Albums: const.ShuffleState.Albums,
                protobuf.ShuffleMode.Songs: const.ShuffleState.Songs,
            }.get(inner.options.shuffleMode, const.ShuffleState.Off)
            self.state.update_state(self.state.active_player)
            _LOGGER.debug("Change shuffle state to %s", state.shuffle)
        elif inner.command == cmd.SeekToPlaybackPosition:
            state.position = inner.options.playbackPosition
            self.state.update_state(self.state.active_player)
            _LOGGER.debug("Seek to position: %d", state.position)
        elif inner.command == cmd.SkipForward:
            state.position += int(inner.options.skipInterval)
            self.state.update_state(self.state.active_player)
            _LOGGER.debug("Skip forward %ds", inner.options.skipInterval)
        elif inner.command == cmd.SkipBackward:
            state.position -= int(inner.options.skipInterval)
            self.state.update_state(self.state.active_player)
            _LOGGER.debug("Skip backwards %d", inner.options.skipInterval)
        else:
            _LOGGER.warning("Unhandled button press: %s", message.inner().command)
            self.send(
                messages.command_result(
                    message.identifier, send_error=protobuf.SendError.NoCommandHandlers
                )
            )
            return

        self.state.last_button_action = None
        self.send(messages.command_result(message.identifier))

    def handle_playback_queue_request(self, message, inner):
        state = self.state.get_player_state(self.state.active_player)

        setstate = messages.create(
            protobuf.SET_STATE_MESSAGE, identifier=message.identifier
        )
        queue = setstate.inner().playbackQueue
        queue.location = 0
        item = queue.contentItems.add()
        item.artworkData = self.state.states[self.state.active_player].artwork
        item.artworkDataWidth = state.artwork_width or 456
        item.artworkDataHeight = state.artwork_height or 789
        self.send(setstate)

    def handle_wake_device(self, message, inner):
        self.send(messages.command_result(message.identifier))
        self.state.powered_on = True
        self._send_device_info(update=True)


class FakeMrpUseCases:
    """Wrapper for altering behavior of a FakeMrpAppleTV instance."""

    def __init__(self, state):
        """Initialize a new FakeMrpUseCases."""
        self.state = state

    def change_volume_control(self, available):
        """Change volume control availability."""
        self.state.volume_control(available)

    def change_artwork(
        self, artwork, mimetype, identifier="artwork", width=None, height=None
    ):
        """Call to change artwork response."""
        metadata = self.state.get_player_state(PLAYER_IDENTIFIER)
        metadata.artwork = artwork
        metadata.artwork_mimetype = mimetype
        metadata.artwork_identifier = identifier
        metadata.artwork_width = width
        metadata.artwork_height = height
        self.state.update_state(PLAYER_IDENTIFIER)

    def change_metadata(self, **kwargs):
        """Change metadata for item via ContentItemUpdate."""
        metadata = self.state.get_player_state(PLAYER_IDENTIFIER)

        # Update saved metadata
        for key, value in kwargs.items():
            setattr(metadata, key, value)

        # Create a temporary metadata instance with requested parameters
        change = PlayingState(**kwargs)
        self.state.item_update(change, PLAYER_IDENTIFIER)

    def change_state(self, **kwargs):
        """Update playing state and set SetStateMessage."""
        metadata = self.state.get_player_state(PLAYER_IDENTIFIER)

        # Update saved metadata
        for key, value in kwargs.items():
            setattr(metadata, key, value)

        self.state.update_state(PLAYER_IDENTIFIER)

    def update_client(self, display_name):
        """Update playing client with new information."""
        self.state.update_client(display_name, PLAYER_IDENTIFIER)

    def nothing_playing(self):
        """Call to put device in idle state."""
        self.state.set_active_player(None)

    def example_video(self, **kwargs):
        """Play some example video."""
        kwargs.setdefault("title", "dummy")
        kwargs.setdefault("paused", True)
        kwargs.setdefault("position", 3)
        kwargs.setdefault("total_time", 123)
        self.video_playing(**kwargs)

    def video_playing(self, paused, title, total_time, position, **kwargs):
        """Call to change what is currently plaing to video."""
        metadata = PlayingState(
            playback_state=ssm.Paused if paused else ssm.Playing,
            title=title,
            total_time=total_time,
            position=position,
            media_type=protobuf.ContentItemMetadata.Video,
            **kwargs,
        )
        self.state.set_player_state(PLAYER_IDENTIFIER, metadata)
        self.state.set_active_player(PLAYER_IDENTIFIER)

    def example_music(self, **kwargs):
        """Play some example music."""
        kwargs.setdefault("paused", True)
        kwargs.setdefault("title", "music")
        kwargs.setdefault("artist", "artist")
        kwargs.setdefault("album", "album")
        kwargs.setdefault("total_time", 49)
        kwargs.setdefault("position", 22)
        kwargs.setdefault("genre", "genre")
        self.music_playing(**kwargs)

    def music_playing(
        self, paused, artist, album, title, genre, total_time, position, **kwargs
    ):
        """Call to change what is currently plaing to music."""
        metadata = PlayingState(
            playback_state=ssm.Paused if paused else ssm.Playing,
            artist=artist,
            album=album,
            title=title,
            genre=genre,
            total_time=total_time,
            position=position,
            media_type=protobuf.ContentItemMetadata.Music,
            **kwargs,
        )
        self.state.set_player_state(PLAYER_IDENTIFIER, metadata)
        self.state.set_active_player(PLAYER_IDENTIFIER)

    def media_is_loading(self):
        """Call to put device in a loading state."""
        metadata = PlayingState(playback_state=ssm.Interrupted)
        self.state.set_player_state(PLAYER_IDENTIFIER, metadata)
        self.state.set_active_player(PLAYER_IDENTIFIER)
