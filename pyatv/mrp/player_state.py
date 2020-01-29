"""Module responsible for keeping track of media player states."""

import asyncio
import logging
from datetime import datetime, timedelta

from pyatv.mrp import protobuf


_LOGGER = logging.getLogger(__name__)


def _cocoa_to_timestamp(time):
    delta = datetime(2001, 1, 1) - datetime(1970, 1, 1)
    time_seconds = (timedelta(seconds=time) + delta).total_seconds()
    return datetime.fromtimestamp(time_seconds)


class PlayerState:
    """Represent what is currently playing on a device."""

    def __init__(self):
        """Initialize a new PlayerState instance."""
        self._playback_state = None
        self.supported_commands = []
        self.timestamp = None
        self.items = []
        self.location = 0

    @property
    def playback_state(self):
        """Playback state of device."""
        if self.metadata and self.metadata.HasField('playbackRate'):
            return 0 < self.metadata.playbackRate > 0

        return self._playback_state

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

    def handle_set_state(self, setstate):
        """Update current state with new data from SetStateMessage."""
        if setstate.HasField('playbackState'):
            self._playback_state = setstate.playbackState

        if setstate.HasField('supportedCommands'):
            self.supported_commands = \
                setstate.supportedCommands.supportedCommands

        if setstate.HasField('playbackStateTimestamp'):
            self.timestamp = _cocoa_to_timestamp(
                int(setstate.playbackStateTimestamp))

        if setstate.HasField('playbackQueue'):
            queue = setstate.playbackQueue
            self.items = queue.contentItems
            self.location = queue.location

    def handle_content_item_update(self, item_update):
        """Update current state with new data from ContentItemUpdate."""
        for updated_item in item_update.contentItems:
            for existing in self.items:
                if updated_item.identifier == existing.identifier:
                    # TODO: Other parts of the ContentItem should be merged as
                    # well, but those are not used right now so will do that
                    # when needed.
                    #
                    # NB: MergeFrom will append repeated fields (which is
                    # likely not what is expected)!
                    existing.metadata.MergeFrom(updated_item.metadata)


class PlayerStateManager:  # pylint: disable=too-few-public-methods
    """Manage state of all media players."""

    def __init__(self, protocol, loop):
        """Initialize a new PlayerStateManager instance."""
        self.protocol = protocol
        self.loop = loop
        self.states = {}
        self.active = None
        self._listener = None
        self._add_listeners()

    def _add_listeners(self):
        self.protocol.add_listener(
            self._handle_set_state, protobuf.SET_STATE_MESSAGE)
        self.protocol.add_listener(
            self._handle_content_item_update,
            protobuf.UPDATE_CONTENT_ITEM_MESSAGE)
        self.protocol.add_listener(
            self._handle_set_now_playing_client,
            protobuf.SET_NOW_PLAYING_CLIENT_MESSAGE)

    @property
    def listener(self):
        """Return current listener."""
        return self._listener

    @listener.setter
    def listener(self, new_listener):
        """Change current listener."""
        self._listener = new_listener
        if self.listener:
            asyncio.ensure_future(
                self.listener.state_updated(), loop=self.loop)

    @property
    def playing(self):
        """Player state for active media player."""
        if self.active:
            return self.states[self.active]
        return PlayerState()

    async def _handle_set_state(self, message, _):
        setstate = message.inner()
        identifier = setstate.playerPath.client.bundleIdentifier

        if identifier not in self.states:
            self.states[identifier] = PlayerState()

        self.states[identifier].handle_set_state(setstate)

        # Only trigger callback if current state changed
        if identifier == self.active:
            if self.listener:
                await self.listener.state_updated()

    async def _handle_content_item_update(self, message, _):
        item_update = message.inner()
        identifier = item_update.playerPath.client.bundleIdentifier

        if identifier in self.states:
            state = self.states[identifier]
            state.handle_content_item_update(item_update)

            # Only trigger callback if current state changed
            if identifier == self.active:
                if self.listener:
                    await self.listener.state_updated()
        else:
            _LOGGER.warning(
                'Received ContentItemUpdate for unknown player %s',
                identifier)

    async def _handle_set_now_playing_client(self, message, _):
        identifier = message.inner().client.bundleIdentifier
        if identifier != self.active:
            self.active = identifier
            _LOGGER.debug('Active player is now %s', self.active)

            if self.listener:
                await self.listener.state_updated()
