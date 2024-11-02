"""Fake MRP Apple TV for tests."""

import asyncio
from datetime import datetime
import logging
import math
import struct
from typing import Dict, List, Optional, Tuple

from google.protobuf.message import Message as ProtobufMessage

from pyatv import const
from pyatv.protocols.mrp import messages, protobuf
from pyatv.protocols.mrp.protobuf import CommandInfo_pb2 as cmd
from pyatv.protocols.mrp.protobuf import PlaybackState
from pyatv.protocols.mrp.protobuf import SendCommandResultMessage as scr
from pyatv.protocols.mrp.server_auth import MrpServerAuth
from pyatv.settings import InfoSettings
from pyatv.support import chacha20, log_protobuf, variant

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

DEFAULT_PLAYER_ID = "MediaRemote-DefaultPlayer"
DEFAULT_PLAYER_NAME = "Default Player"

BUILD_NUMBER = "18M60"
OS_VERSION = "14.7"  # Must match BUILD_NUMBER (take from device_info.py)
DEVICE_MODEL = "AppleTV6,2"

DEVICE_UID = "E510C430-B01D-45DF-B558-6EA6F8251069"

VOLUME_STEP = 0.05


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
    if hasattr(metadata, "artwork_url"):
        md.artworkURL = metadata.artwork_url
    if metadata.artwork_identifier:
        md.artworkIdentifier = metadata.artwork_identifier
    if metadata.series_name:
        md.seriesName = metadata.series_name
    if metadata.season_number:
        md.seasonNumber = metadata.season_number
    if metadata.episode_number:
        md.episodeNumber = metadata.episode_number
    if metadata.content_identifier:
        md.contentIdentifier = metadata.content_identifier
    if metadata.itunes_store_identifier:
        md.iTunesStoreIdentifier = metadata.itunes_store_identifier


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
    if metadata.app_name:
        client.displayName = metadata.app_name

    player = inner.playerPath.player
    player.identifier = DEFAULT_PLAYER_ID
    player.displayName = DEFAULT_PLAYER_NAME
    return set_state


class PlayingState:
    def __init__(self, **kwargs):
        """Initialize a new PlayingState."""
        self.identifier = kwargs.get("identifier")
        self.playback_state = kwargs.get("playback_state")
        self.title = kwargs.get("title")
        self.series_name = kwargs.get("series_name")
        self.artist = kwargs.get("artist")
        self.album = kwargs.get("album")
        self.genre = kwargs.get("genre")
        self.total_time = kwargs.get("total_time")
        self.position = kwargs.get("position")
        self.season_number = kwargs.get("season_number")
        self.episode_number = kwargs.get("episode_number")
        self.repeat = kwargs.get("repeat")
        self.shuffle = kwargs.get("shuffle")
        self.media_type = kwargs.get("media_type")
        self.playback_rate = kwargs.get("playback_rate")
        self.supported_commands = kwargs.get("supported_commands")
        self.artwork = kwargs.get("artwork")
        self.artwork_identifier = kwargs.get("artwork_identifier")
        self.artwork_mimetype = kwargs.get("artwork_mimetype")
        self.artwork_width = kwargs.get("artwork_width")
        self.artwork_height = kwargs.get("artwork_height")
        self.skip_time = kwargs.get("skip_time")
        self.app_name = kwargs.get("app_name")
        self.content_identifier = kwargs.get("content_identifier")
        self.itunes_store_identifier = kwargs.get("itunes_store_identifier")


class FakeMrpState:
    def __init__(self):
        """State of a fake MRP device."""
        self.clients = []
        self.outstanding_keypresses: Dict[Tuple[int, int], float] = {}
        self.last_button_pressed: Optional[str] = None
        self.last_button_action: Optional[const.InputAction] = None
        self.connection_state = None
        self.states = {}
        self.active_player = None
        self.powered_on = True
        self.has_authenticated = False
        self.heartbeat_count = 0
        self.volume: float = 0.5
        self.cluster_id: Optional[str] = None
        self.output_devices: List[str] = [DEVICE_UID]

    def _send(self, msg):
        for client in self.clients:
            client.send_to_client(msg)

    def _send_device_info(self):
        for client in self.clients:
            client._send_device_info(update=True)

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
            raise Exception(f"invalid player: {identifier}")

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

        player = inner.playerPath.player
        player.identifier = DEFAULT_PLAYER_ID
        player.displayName = DEFAULT_PLAYER_NAME

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

    def set_cluster_id(self, cluster_id):
        self.cluster_id = cluster_id
        self._send_device_info()

    def volume_control(self, available, support_absolute=True, support_relative=True):
        if support_absolute and support_relative:
            capabilities = protobuf.VolumeCapabilities.Both
        elif support_absolute:
            capabilities = protobuf.VolumeCapabilities.Absolute
        elif support_relative:
            capabilities = protobuf.VolumeCapabilities.Relative
        else:
            capabilities = None

        msg = messages.create(protobuf.VOLUME_CONTROL_AVAILABILITY_MESSAGE)
        msg.inner().volumeControlAvailable = available
        msg.inner().volumeCapabilities = capabilities
        self._send(msg)

        msg = messages.create(protobuf.VOLUME_CONTROL_CAPABILITIES_DID_CHANGE_MESSAGE)
        msg.inner().capabilities.volumeControlAvailable = available
        msg.inner().capabilities.volumeCapabilities = capabilities
        msg.inner().outputDeviceUID = DEVICE_UID
        self._send(msg)

    def default_supported_commands(self, commands):
        msg = messages.create(protobuf.SET_DEFAULT_SUPPORTED_COMMANDS_MESSAGE)
        supported_commands = msg.inner().supportedCommands.supportedCommands
        for command in commands:
            item = supported_commands.add()
            item.command = command
            item.enabled = True
        msg.inner().playerPath.client.bundleIdentifier = PLAYER_IDENTIFIER
        self._send(msg)

    def set_volume(self, volume, device_uid):
        if 0 <= volume <= 1:
            self.volume = volume

            msg = messages.create(protobuf.VOLUME_DID_CHANGE_MESSAGE)
            msg.inner().outputDeviceUID = device_uid
            msg.inner().volume = volume
            self._send(msg)
        else:
            _LOGGER.debug("Value %f out of range", volume)

    def add_output_devices(self, devices):
        for device in devices:
            if device not in self.output_devices:
                self.output_devices.append(device)
        self._send_device_info()

    def remove_output_devices(self, devices):
        for device in devices:
            self.output_devices.remove(device)
        self._send_device_info()

    def set_output_devices(self, devices):
        self.output_devices[:] = devices
        self._send_device_info()


class FakeMrpServiceFactory:
    def __init__(self, state, app, loop):
        self.state = state
        self.app = app
        self.loop = loop
        self.server = None

    async def start(self, start_web_server: bool):
        def _server_factory():
            try:
                return FakeMrpService(self.state, self.app, self.loop)
            except Exception:
                _LOGGER.exception("failed to create server")
                raise

        coro = self.loop.create_server(_server_factory, "0.0.0.0")
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
        super().__init__(DEVICE_NAME)
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

    def enable_encryption(self, output_key: bytes, input_key: bytes) -> None:
        """Enable encryption with specified keys."""
        self.chacha = chacha20.Chacha20Cipher8byteNonce(output_key, input_key)
        self.state.has_authenticated = True

    def send_to_client(self, message: ProtobufMessage) -> None:
        if not self.transport:
            return

        data = message.SerializeToString()
        if self.chacha:
            data = self.chacha.encrypt(data)

        length = variant.write_variant(len(data))
        self.transport.write(length + data)
        log_protobuf(_LOGGER, ">> Send: Protobuf", message)

    def _send_device_info(self, identifier=None, update=False):
        info = InfoSettings()
        info.name = DEVICE_NAME
        info.os_build = BUILD_NUMBER
        resp = messages.device_information(info, DEVICE_UID, update=update)
        if identifier:
            resp.identifier = identifier
        resp.inner().logicalDeviceCount = 1 if self.state.powered_on else 0
        resp.inner().deviceUID = DEVICE_UID
        resp.inner().modelID = DEVICE_MODEL
        resp.inner().isGroupLeader = bool(len(self.state.output_devices) > 0)
        resp.inner().isProxyGroupPlayer = bool(
            len(self.state.output_devices) > 0
            and DEVICE_UID not in self.state.output_devices
        )
        for device in self.state.output_devices:
            if device == DEVICE_UID:
                continue
            device_info = protobuf.DeviceInfoMessage()
            device_info.name = f"Device {device[:2]}"
            device_info.deviceUID = device
            resp.inner().groupedDevices.append(device_info)
        self.send_to_client(resp)

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
                _LOGGER.exception("No message handler for %s", parsed)
            except Exception:
                _LOGGER.exception("Error while dispatching message")

    def handle_device_info(self, message, inner):
        self._send_device_info(update=False, identifier=message.identifier)

    def handle_set_connection_state(self, message, inner):
        _LOGGER.debug("Changed connection state to %d", inner.state)
        self.state.connection_state = inner.state

    def handle_client_updates_config(self, message, inner):
        for identifier, metadata in self.state.states.items():
            self.send_to_client(_set_state_message(metadata, identifier))

        # Trigger sending of SetNowPlayingClientMessage
        if self.state.active_player:
            self.state.set_active_player(self.state.active_player)

        if message.identifier is not None:
            self.send_to_client(messages.create(0, identifier=message.identifier))

    def handle_get_keyboard_session(self, message, inner):
        # This message has a lot more fields, but pyatv currently
        # not use them so ignore for now
        self.send_to_client(
            messages.create(protobuf.KEYBOARD_MESSAGE, identifier=message.identifier)
        )

    def handle_send_hid_event(self, message, inner):
        outstanding = self.state.outstanding_keypresses

        # These corresponds to the bytes mapping to pressed key (see
        # send_hid_event in pyatv/protocols/mrp/messages.py)
        start = inner.hidEventData[43:49]
        use_page, usage, down_press = struct.unpack(">HHH", start)

        if down_press == 1:
            outstanding[(use_page, usage)] = stub_sleep()
            self.send_to_client(messages.create(0, identifier=message.identifier))
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
                self.send_to_client(messages.create(0, identifier=message.identifier))

                # Special cases for some buttons
                if pressed_key == "volumeup" and not math.isclose(
                    self.state.volume, 100.0
                ):
                    self.state.set_volume(
                        min(self.state.volume + VOLUME_STEP, 100.0), DEVICE_UID
                    )
                elif pressed_key == "volumedown" and not math.isclose(
                    self.state.volume, 0.0
                ):
                    self.state.set_volume(
                        max(self.state.volume - VOLUME_STEP, 0.0), DEVICE_UID
                    )
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
            self.send_to_client(
                messages.command_result(
                    message.identifier, send_error=protobuf.SendError.NoCommandHandlers
                )
            )
            return

        self.state.last_button_action = None
        self.send_to_client(messages.command_result(message.identifier))

    def handle_playback_queue_request(self, message, inner):
        state = self.state.get_player_state(self.state.active_player)

        setstate = messages.create(
            protobuf.SET_STATE_MESSAGE, identifier=message.identifier
        )

        artwork_data = self.state.states[self.state.active_player].artwork
        if artwork_data:
            queue = setstate.inner().playbackQueue
            queue.location = 0
            item = queue.contentItems.add()
            item.artworkData = artwork_data
            item.artworkDataWidth = state.artwork_width or 456
            item.artworkDataHeight = state.artwork_height or 789
        self.send_to_client(setstate)

    def handle_wake_device(self, message, inner):
        self.send_to_client(messages.command_result(message.identifier))
        self.state.powered_on = True
        self._send_device_info(update=True)

    def handle_generic(self, message, inner):
        # Generic message is used by pyatv for heartbeats
        self.state.heartbeat_count += 1
        _LOGGER.debug(
            "Received heartbeat (total count: %d)", self.state.heartbeat_count
        )
        self.send_to_client(
            messages.create(
                protobuf.ProtocolMessage.UNKNOWN_MESSAGE, identifier=message.identifier
            )
        )

    def handle_set_volume(self, message, inner):
        _LOGGER.debug("Setting volume to %f", inner.volume)
        self.state.set_volume(inner.volume, inner.outputDeviceUID)
        self.send_to_client(
            messages.create(
                protobuf.ProtocolMessage.UNKNOWN_MESSAGE, identifier=message.identifier
            )
        )

    def handle_modify_output_context_request(self, message, inner):
        if inner.addingDevices:
            _LOGGER.debug("Adding output devices: %s", inner.addingDevices)
            self.state.add_output_devices(list(inner.addingDevices))
        if inner.removingDevices:
            _LOGGER.debug("Removing output devices: %s", inner.removingDevices)
            self.state.remove_output_devices(list(inner.removingDevices))
        if inner.settingDevices:
            _LOGGER.debug("Setting output devices: %s", inner.settingDevices)
            self.state.set_output_devices(list(inner.settingDevices))


class FakeMrpUseCases:
    """Wrapper for altering behavior of a FakeMrpAppleTV instance."""

    def __init__(self, state):
        """Initialize a new FakeMrpUseCases."""
        self.state = state

    def set_cluster_id(self, cluster_id):
        self.state.set_cluster_id(cluster_id)

    def change_volume_control(
        self, available, support_absolute=True, support_relative=True
    ):
        """Change volume control availability."""
        self.state.volume_control(
            available,
            support_absolute=support_absolute,
            support_relative=support_relative,
        )

        # Device always sends current volume if controls are available
        if available:
            self.state.set_volume(self.state.volume, DEVICE_UID)

    def change_artwork(
        self, artwork, mimetype, identifier="artwork", width=None, height=None, url=None
    ):
        """Call to change artwork response."""
        metadata = self.state.get_player_state(PLAYER_IDENTIFIER)
        metadata.artwork = artwork
        metadata.artwork_mimetype = mimetype
        metadata.artwork_identifier = identifier
        metadata.artwork_width = width
        metadata.artwork_height = height
        if url is not None:
            metadata.artwork_url = url
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

    def change_state(self, player=PLAYER_IDENTIFIER, **kwargs):
        """Update playing state and set SetStateMessage."""
        metadata = self.state.get_player_state(player)

        # Update saved metadata
        for key, value in kwargs.items():
            setattr(metadata, key, value)

        self.state.update_state(PLAYER_IDENTIFIER)

    def update_client(self, display_name, player=PLAYER_IDENTIFIER):
        """Update playing client with new information."""
        self.state.update_client(display_name, player)

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

    def video_playing(
        self,
        paused,
        title,
        total_time,
        position,
        player=PLAYER_IDENTIFIER,
        app_name=APP_NAME,
        **kwargs
    ):
        """Call to change what is currently plaing to video."""
        fields = {
            "playback_state": PlaybackState.Paused if paused else PlaybackState.Playing,
            "playback_rate": 0.0 if paused else 1.0,
            "title": title,
            "total_time": total_time,
            "position": position,
            "media_type": protobuf.ContentItemMetadata.Video,
            "app_name": app_name,
        }
        fields.update(kwargs)
        self.state.set_player_state(player, PlayingState(**fields))
        self.state.set_active_player(player)

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
        fields = {
            "playback_state": PlaybackState.Paused if paused else PlaybackState.Playing,
            "playback_rate": 0.0 if paused else 1.0,
            "artist": artist,
            "album": album,
            "title": title,
            "genre": genre,
            "total_time": total_time,
            "position": position,
            "media_type": protobuf.ContentItemMetadata.Music,
        }
        fields.update(kwargs)
        self.state.set_player_state(PLAYER_IDENTIFIER, PlayingState(**fields))
        self.state.set_active_player(PLAYER_IDENTIFIER)

    def example_tv(self, **kwargs):
        kwargs.setdefault("paused", False)
        kwargs.setdefault("series_name", "tvshow")
        kwargs.setdefault("total_time", 123)
        kwargs.setdefault("position", 5)
        kwargs.setdefault("season_number", 12)
        kwargs.setdefault("episode_number", 3)
        self.tv_playing(**kwargs)

    def tv_playing(
        self,
        paused,
        series_name,
        total_time,
        position,
        season_number,
        episode_number,
        **kwargs
    ):
        """Call to change what is currently playing to TV."""
        fields = {
            "playback_state": PlaybackState.Paused if paused else PlaybackState.Playing,
            "playback_rate": 0.0 if paused else 1.0,
            "series_name": series_name,
            "total_time": total_time,
            "position": position,
            "season_number": season_number,
            "episode_number": episode_number,
            "media_type": protobuf.ContentItemMetadata.Video,
        }
        fields.update(kwargs)
        self.state.set_player_state(PLAYER_IDENTIFIER, PlayingState(**fields))
        self.state.set_active_player(PLAYER_IDENTIFIER)

    def media_is_loading(self):
        """Call to put device in a loading state."""
        metadata = PlayingState(playback_state=PlaybackState.Interrupted)
        self.state.set_player_state(PLAYER_IDENTIFIER, metadata)
        self.state.set_active_player(PLAYER_IDENTIFIER)

    def default_supported_commands(self, commands):
        """Call to set default supported commands."""
        self.state.default_supported_commands(commands)

    def set_volume(self, volume: float, device_uid: str) -> None:
        """Change current volume."""
        self.state.set_volume(volume, device_uid)
