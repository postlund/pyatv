"""Example for device authentication."""

import sys
import asyncio
from pyatv import (exceptions, helpers)


@asyncio.coroutine
def authenticate_with_device(atv):
    """Perform device authentication and print credentials."""
    credentials = yield from atv.airplay.generate_credentials()
    yield from atv.airplay.load_credentials(credentials)

    try:
        yield from atv.airplay.start_authentication()
        pin = input('PIN Code: ')
        yield from atv.airplay.finish_authentication(pin)
        print('Credentials: {0}'.format(credentials))

    except exceptions.DeviceAuthenticationError:
        print('Failed to authenticate', file=sys.stderr)


helpers.auto_connect(authenticate_with_device)
