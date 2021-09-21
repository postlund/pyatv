"""Support functions used in library."""

import asyncio
import binascii
import functools
import logging
from os import environ
import warnings

from google.protobuf.text_format import MessageToString

from pyatv import exceptions

_PROTOBUF_LINE_LENGTH = 150
_BINARY_LINE_LENGTH = 512


def _shorten(text, length):
    return text if len(text) < length else text[: length - 3] + "..."


def _log_value(value):
    if value is None:
        return ""
    if isinstance(value, bytes):
        return binascii.hexlify(bytearray(value or b"")).decode()
    return str(value)


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
            f"{k}={_shorten(_log_value(v), line_length)}"
            for k, v in sorted(kwargs.items())
        )

        logger.debug("%s (%s)", message, ", ".join(output))


def log_protobuf(logger, text, message):
    """Log protobuf message and shorten line length."""
    if logger.isEnabledFor(logging.DEBUG):
        override_length = int(environ.get("PYATV_PROTOBUF_MAX_LINE", 0))
        line_length = override_length or _PROTOBUF_LINE_LENGTH

        lines = MessageToString(message, print_unknown_fields=True).splitlines()
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
            f"Call to deprecated function {func.__name__}.",
            category=DeprecationWarning,
            stacklevel=2,
        )
        warnings.simplefilter("default", DeprecationWarning)  # reset filter
        return func(*args, **kwargs)

    return new_func


def map_range(
    value: float, in_min: float, in_max: float, out_min: float, out_max: float
) -> float:
    """Map a value in one range to another."""
    if in_max - in_min <= 0.0:
        raise ValueError("invalid input range")
    if out_max - out_min <= 0.0:
        raise ValueError("invalid output range")
    if value < in_min or value > in_max:
        raise ValueError("input value out of range")
    return (value - in_min) * (out_max - out_min) / (in_max - in_min) + out_min
