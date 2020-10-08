"""Support functions used in library."""

import asyncio
import inspect
import logging
import binascii
import warnings
import functools
from os import environ

from google.protobuf.text_format import MessageToString

from pyatv import exceptions


_PROTOBUF_LINE_LENGTH = 150
_BINARY_LINE_LENGTH = 512

_HAS_PRINT_UNKNOWN = (
    "print_unknown_fields" in inspect.signature(MessageToString).parameters
)


def _shorten(text, length):
    return text if len(text) < length else text[: length - 3] + "..."


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
def log_binary(logger, message, level=logging.DEBUG, **kwargs):
    """Log binary data if debug is enabled."""
    if logger.isEnabledFor(level):
        override_length = int(environ.get("PYATV_BINARY_MAX_LINE", 0))
        line_length = override_length or _BINARY_LINE_LENGTH

        output = (
            "{0}={1}".format(
                k, _shorten(binascii.hexlify(bytearray(v or b"")).decode(), line_length)
            )
            for k, v in sorted(kwargs.items())
        )

        logger.debug("%s (%s)", message, ", ".join(output))


def log_protobuf(logger, text, message):
    """Log protobuf message and shorten line length."""
    if logger.isEnabledFor(logging.DEBUG):
        override_length = int(environ.get("PYATV_PROTOBUF_MAX_LINE", 0))
        line_length = override_length or _PROTOBUF_LINE_LENGTH

        # Workaround to support older versions of protobuf (remove this
        # at some point)
        kwargs = {}
        if _HAS_PRINT_UNKNOWN:
            kwargs["print_unknown_fields"] = True

        lines = MessageToString(message, **kwargs).splitlines()
        msg_str = "\n".join([_shorten(x, line_length) for x in lines])

        logger.debug("%s: %s", text, msg_str)


# https://stackoverflow.com/questions/2536307/
#   decorators-in-the-python-standard-lib-deprecated-specifically
def deprecated(func):
    """Decorate functions that are deprecated."""

    @functools.wraps(func)
    def new_func(*args, **kwargs):
        warnings.simplefilter("always", DeprecationWarning)  # turn off filter
        warnings.warn(
            "Call to deprecated function {}.".format(func.__name__),
            category=DeprecationWarning,
            stacklevel=2,
        )
        warnings.simplefilter("default", DeprecationWarning)  # reset filter
        return func(*args, **kwargs)

    return new_func
