"""Device pairing and derivation of encryption keys."""

import logging
import binascii
from collections import namedtuple

from pyatv import exceptions, net
from pyatv.const import Protocol
from pyatv.interface import PairingHandler
from pyatv.airplay.srp import (SRPAuthHandler, new_credentials)
from pyatv.airplay.auth import DeviceAuthenticator
from pyatv.support import error_handler

_LOGGER = logging.getLogger(__name__)

AuthData = namedtuple('AuthData', 'identifier seed credentials')


class AirPlayPairingHandler(PairingHandler):
    """Base class for API used to pair with an Apple TV."""

    def __init__(self, config, session, _):
        """Initialize a new MrpPairingHandler."""
        super().__init__(session, config.get_service(Protocol.AirPlay))
        self.srp = SRPAuthHandler()
        self.http = net.HttpSession(
            session,
            'http://{0}:{1}/'.format(config.address, self.service.port))
        self.auther = DeviceAuthenticator(self.http, self.srp)
        self.auth_data = self._setup_credentials()
        self.srp.initialize(binascii.unhexlify(self.auth_data.seed))
        self.pairing_complete = False
        self.pin_code = None

    def _setup_credentials(self):
        credentials = self.service.credentials

        # If service has credentials, use those. Otherwise generate new.
        if self.service.credentials is None:
            identifier, seed = new_credentials()
            credentials = '{0}:{1}'.format(identifier, seed.decode().upper())
        else:
            split = credentials.split(':')
            identifier = split[0]
            seed = split[1]
        return AuthData(identifier, seed, credentials)

    @property
    def has_paired(self):
        """If a successful pairing has been performed."""
        return self.pairing_complete

    def begin(self):
        """Start pairing process."""
        _LOGGER.debug('Starting AirPlay pairing with credentials %s',
                      self.auth_data.credentials)
        self.pairing_complete = False
        return error_handler(self.auther.start_authentication,
                             exceptions.PairingError)

    async def finish(self):
        """Stop pairing process."""
        if not self.pin_code:
            raise exceptions.PairingError('no pin given')

        await error_handler(self.auther.finish_authentication,
                            exceptions.PairingError,
                            self.auth_data.identifier,
                            self.pin_code)

        self.service.credentials = self.auth_data.credentials
        self.pairing_complete = True

    def pin(self, pin):
        """Pin code used for pairing."""
        self.pin_code = str(pin).zfill(4)

    @property
    def device_provides_pin(self):
        """Return True if remote device presents PIN code, else False."""
        return True
