"""Implementation of external API for AirPlay."""

import logging
import binascii

from pyatv import const
from pyatv.interface import AirPlay

from pyatv.airplay.srp import SRPAuthHandler
from pyatv.airplay.auth import AuthenticationVerifier

_LOGGER = logging.getLogger(__name__)


class AirPlayAPI(AirPlay):  # pylint: disable=too-few-public-methods
    """Implementation of API for AirPlay support."""

    def __init__(self, config, http, airplay_player):
        """Initialize a new AirPlayInternal instance."""
        self.config = config
        self.player = airplay_player
        self.identifier = None
        self.srp = SRPAuthHandler()
        self.verifier = AuthenticationVerifier(http, self.srp)
        self._load_credentials()

    def _load_credentials(self):
        service = self.config.get_service(const.PROTOCOL_AIRPLAY)
        if service.credentials is None:
            _LOGGER.debug('No AirPlay credentials loaded')
            return

        split = service.credentials.split(':')
        self.identifier = split[0]
        self.srp.initialize(binascii.unhexlify(split[1]))
        _LOGGER.debug(
            'Loaded AirPlay credentials: %s',
            service.credentials)

    def _verify_authenticated(self):
        """Check if loaded credentials are verified."""
        return self.verifier.verify_authed()

    async def play_url(self, url, **kwargs):
        """Play media from an URL on the device.

        Note: This method will not yield until the media has finished playing.
        The Apple TV requires the request to stay open during the entire
        play duration.
        """
        # If credentials have been loaded, do device verification first
        if self.identifier:
            await self._verify_authenticated()

        position = int(kwargs.get('position', 0))
        return await self.player.play_url(url, position)
