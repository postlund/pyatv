"""Implementation of the MediaRemoteTV Protocol used by ATV4 and later."""

import logging
import asyncio

from pyatv.interface import (AppleTV, RemoteControl, Metadata,
                             Playing, PushUpdater)

_LOGGER = logging.getLogger(__name__)


class MrpRemoteControl(RemoteControl):
    """Implementation of API for controlling an Apple TV."""

    pass


class MrpPlaying(Playing):
    """Implementation of API for retrieving what is playing."""

    pass


class MrpMetadata(Metadata):
    """Implementation of API for retrieving metadata."""

    pass


class MrpPushUpdater(PushUpdater):
    """Implementation of API for handling push update from an Apple TV."""

    pass


class MrpAppleTV(AppleTV):
    """Implementation of API support for Apple TV."""

    # This is a container class so it's OK with many attributes
    # pylint: disable=too-many-instance-attributes
    def __init__(self, loop, session, details, airplay):
        """Initialize a new Apple TV."""
        super().__init__()

        self._atv_remote = MrpRemoteControl()
        self._atv_metadata = MrpMetadata()
        self._atv_push_updater = MrpPushUpdater()
        self._airplay = airplay

    @asyncio.coroutine
    def login(self):
        """Perform an explicit login."""
        _LOGGER.debug('Login called')

    @asyncio.coroutine
    def logout(self):
        """Perform an explicit logout.

        Must be done when session is no longer needed to not leak resources.
        """
        _LOGGER.debug('Logout called')

    @property
    def remote_control(self):
        """Return API for controlling the Apple TV."""
        return self._atv_remote

    @property
    def metadata(self):
        """Return API for retrieving metadata from Apple TV."""
        return self._atv_metadata

    @property
    def push_updater(self):
        """Return API for handling push update from the Apple TV."""
        return self._atv_push_updater

    @property
    def airplay(self):
        """Return API for working with AirPlay."""
        return self._airplay
