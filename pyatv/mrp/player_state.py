"""Module responsible for keeping track of media player states."""

import math
import logging
import weakref
from copy import deepcopy
from typing import Dict, Optional, List

from pyatv.mrp import protobuf as pb


_LOGGER = logging.getLogger(__name__)


class PlayerState:
    """Represent what is currently playing on a device."""

    def __init__(self, player: pb.NowPlayingPlayer):
        """Initialize a new PlayerState instance."""
        self._playback_state = None
        self.supported_commands: List[pb.CommandInfo] = []
        self.items: List[pb.ContentItem] = []
        self.location: int = 0

        self.identifier: Optional[str] = player.identifier
        self.display_name: Optional[str] = None
        self.update(player)

    @property
    def is_valid(self):
        """Return if player has a valid identifier."""
        return self.identifier is not None and self.identifier != ""

    def update(self, player: pb.NowPlayingPlayer):
        """Update player metadata."""
        self.display_name = player.displayName or self.display_name

    @property
    def playback_state(self):
        """Playback state of device."""
        # if playback state has not been received, assume player is not playing
        # anything (i.e. idle)
        if self._playback_state is None:
            return None

        # If player is considered paused, no content is playing
        if self._playback_state == pb.PlaybackState.Paused:
            # ...unless something is in the queue...
            if self.metadata is not None:
                return pb.PlaybackState.Paused
            return None

        # All other states than playing (and paused) should pass through
        if self._playback_state != pb.PlaybackState.Playing:
            return self._playback_state

        playback_rate = self.metadata_field("playbackRate")
        if playback_rate is None:
            return self._playback_state

        if math.isclose(playback_rate, 0.0):
            return pb.PlaybackState.Paused
        if math.isclose(playback_rate, 1.0):
            return pb.PlaybackState.Playing
        return pb.PlaybackState.Seeking

    @property
    def metadata(self):
        """Metadata of currently playing item."""
        if len(self.items) >= (self.location + 1):
            return self.items[self.location].metadata
        return None

    @property
    def item_identifier(self):
        """Return identifier of current item in queue."""
        if len(self.items) >= (self.location + 1):
            return self.items[self.location].identifier
        return None

    def metadata_field(self, field):
        """Return a specific metadata field or None if missing."""
        metadata = self.metadata
        if metadata and metadata.HasField(field):
            return getattr(metadata, field)
        return None

    def command_info(self, command):
        """Return supported command info."""
        for cmd in self.supported_commands:
            if cmd.command == command:
                return cmd
        return None

    def handle_set_state(self, setstate):
        """Update current state with new data from SetStateMessage."""
        if setstate.HasField("playbackState"):
            self._playback_state = setstate.playbackState

        if setstate.HasField("supportedCommands"):
            self.supported_commands = deepcopy(
                setstate.supportedCommands.supportedCommands
            )
        if setstate.HasField("playbackQueue"):
            queue = setstate.playbackQueue
            self.items = deepcopy(queue.contentItems)
            self.location = queue.location

    def handle_content_item_update(self, item_update):
        """Update current state with new data from ContentItemUpdate."""
        for updated_item in item_update.contentItems:
            for existing in self.items:
                if updated_item.identifier == existing.identifier:
                    # Other parts of the ContentItem should be merged as
                    # well, but those are not used right now so will do that
                    # when needed.
                    #
                    # NB: MergeFrom will append repeated fields (which is
                    # likely not what is expected)!
                    existing.metadata.MergeFrom(updated_item.metadata)

    def __eq__(self, other):
        """Compare if instance is equal to other instance."""
        return other and self.identifier == other.identifier


class Client:
    """Represent an MRP media player client."""

    def __init__(self, client: pb.NowPlayingClient):
        """Initialize a new Client instance."""
        self.bundle_identifier: str = client.bundleIdentifier
        self.display_name: Optional[str] = None
        self.players: Dict[str, PlayerState] = {}
        self.update(client)

    def update(self, client: pb.NowPlayingClient):
        """Update client metadata."""
        self.display_name = client.displayName or self.display_name


class PlayerStateManager:
    """Manage state of all media players."""

    def __init__(self, protocol):
        """Initialize a new PlayerStateManager instance."""
        self.protocol = protocol
        self.volume_controls_available = None
        self._active_client = None
        self._active_player = None
        self._clients: Dict[str, Client] = {}
        self._listener = None
        self._add_listeners()

    def _add_listeners(self) -> None:
        listeners = {
            pb.SET_STATE_MESSAGE: self._handle_set_state,
            pb.UPDATE_CONTENT_ITEM_MESSAGE: self._handle_content_item_update,
            pb.SET_NOW_PLAYING_CLIENT_MESSAGE: self._handle_set_now_playing_client,
            pb.SET_NOW_PLAYING_PLAYER_MESSAGE: self._handle_set_now_playing_player,
            pb.UPDATE_CLIENT_MESSAGE: self._handle_update_client,
            pb.REMOVE_CLIENT_MESSAGE: self._handle_remove_client,
            pb.REMOVE_PLAYER_MESSAGE: self._handle_remove_player,
            pb.VOLUME_CONTROL_AVAILABILITY_MESSAGE: self._volume_control_availability,
        }
        for message, handler in listeners.items():
            self.protocol.add_listener(handler, message)

    def get_client(self, client: pb.NowPlayingClient) -> Client:
        """Return client based on player path."""
        bundle = client.bundleIdentifier
        if bundle not in self._clients:
            self._clients[bundle] = Client(client)
        return self._clients[bundle]

    def get_player(self, player_path: pb.PlayerPath) -> PlayerState:
        """Return player based on a player path."""
        client = self.get_client(player_path.client)

        player_id = player_path.player.identifier
        if player_id not in client.players:
            client.players[player_id] = PlayerState(player_path.player)
        return client.players[player_id]

    @property
    def listener(self):
        """Return current listener."""
        if self._listener is None:
            return None
        return self._listener()

    @listener.setter
    def listener(self, new_listener):
        """Change current listener."""
        if new_listener is not None:
            self._listener = weakref.ref(new_listener)
        else:
            self._listener = None

    @property
    def client(self) -> Optional[Client]:
        """Return currently active client."""
        return self._active_client

    @property
    def playing(self):
        """Player state for active media player."""
        if self._active_player:
            return self._active_player
        if self._active_client:
            default_player = self._active_client.players.get(
                "MediaRemote-DefaultPlayer"
            )
            if default_player:
                return default_player
        return PlayerState(pb.NowPlayingPlayer())

    async def _handle_set_state(self, message, _):
        setstate = message.inner()

        player = self.get_player(setstate.playerPath)
        player.handle_set_state(setstate)

        await self._state_updated(player=player)

    async def _handle_content_item_update(self, message, _):
        item_update = message.inner()

        player = self.get_player(item_update.playerPath)
        player.handle_content_item_update(item_update)

        await self._state_updated(player=player)

    async def _handle_set_now_playing_client(self, message, _):
        self._active_client = self.get_client(message.inner().client)

        _LOGGER.debug("Active client is now %s", self._active_client.bundle_identifier)

        await self._state_updated()

    async def _handle_set_now_playing_player(self, message, _):
        self._active_player = self.get_player(message.inner().playerPath)

        if self._active_player.is_valid:
            _LOGGER.debug(
                "Active player is now %s (%s)",
                self._active_player.identifier,
                self._active_player.display_name,
            )
        else:
            _LOGGER.debug("Active player no longer set")

        await self._state_updated()

    async def _handle_remove_client(self, message, _):
        client_to_remove = message.inner().client

        if client_to_remove.bundleIdentifier in self._clients:
            client = self._clients[client_to_remove.bundleIdentifier]
            del self._clients[client_to_remove.bundleIdentifier]

            if client == self._active_client:
                self._active_client = None
                await self._state_updated()

    async def _handle_remove_player(self, message, _):
        player_to_remove = message.inner().playerPath

        player = self.get_player(player_to_remove)
        if player.is_valid:
            client = self.get_client(player_to_remove.client)
            del client.players[player.identifier]

            removed = False
            if player == self._active_player:
                self._active_player = None
                removed = True
            if client == self._active_client:
                self._active_client = None
                removed = True

            if removed:
                await self._state_updated()

    async def _handle_update_client(self, message, _):
        update_client = message.inner()

        client = self.get_client(update_client.client)
        client.update(update_client.client)

        await self._state_updated(client=client)

    async def _volume_control_availability(self, message, _):
        self.volume_controls_available = message.inner().volumeControlAvailable
        _LOGGER.debug(
            "Volume control availability is now %s", self.volume_controls_available
        )

        await self._state_updated()

    async def _state_updated(self, client=None, player=None):
        is_active_client = client == self.client
        is_active_player = player == self.playing
        is_always = client is None and player is None

        if is_active_client or is_active_player or is_always:
            if self.listener:
                await self.listener.state_updated()
