"""Support functions used in library."""

import asyncio
import logging
import binascii

from pyatv import exceptions


async def error_handler(func, fallback, *args, **kwargs):
    """Call a function and re-map exceptions to match pyatv interface."""
    try:
        return await func(*args, **kwargs)
    except (OSError, asyncio.TimeoutError) as ex:
        raise exceptions.ConnectionFailedError(str(ex)) from ex
    except exceptions.BackOffError:
        raise
    except exceptions.NoCredentialsError:
        raise
    except Exception as ex:
        raise fallback(str(ex)) from ex


# Special log method to avoid hexlify conversion if debug is on
def log_binary(logger, message, **kwargs):
    """Log binary data if debug is enabled."""
    if logger.isEnabledFor(logging.DEBUG):
        output = ('{0}={1}'.format(k, binascii.hexlify(
            bytearray(v)).decode()) for k, v in sorted(kwargs.items()))
        logger.debug('%s (%s)', message, ', '.join(output))
