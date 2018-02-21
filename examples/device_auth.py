"""Example for device authentication."""

import sys
from pyatv import (exceptions, helpers)


async def authenticate_with_device(atv):
    """Perform device authentication and print credentials."""
    credentials = await atv.airplay.generate_credentials()
    await atv.airplay.load_credentials(credentials)

    try:
        await atv.airplay.start_authentication()
        pin = input('PIN Code: ')
        await atv.airplay.finish_authentication(pin)
        print('Credentials: {0}'.format(credentials))

    except exceptions.DeviceAuthenticationError:
        print('Failed to authenticate', file=sys.stderr)


helpers.auto_connect(authenticate_with_device)
