"""Support functions used in library."""

import asyncio
import binascii
import functools
import logging
from os import environ, path
from typing import Any, List, Sequence, Union, get_origin, get_args
import warnings

from google.protobuf.text_format import MessageToString

import pyatv
from pyatv import exceptions
from pyatv.support.pydantic_compat import BaseModel

_PROTOBUF_LINE_LENGTH = 150
_BINARY_LINE_LENGTH = 512


def _shorten(text: Union[str, bytes], length: int) -> str:
    if isinstance(text, str):
        return text if len(text) < length else (text[: length - 3] + "...")
    return str(text if len(text) < length else (text[: length - 3] + b"..."))


def _log_value(value):
    if value is None:
        return ""
    if isinstance(value, bytes):
        return binascii.hexlify(bytearray(value or b"")).decode()
    return str(value)


def prettydataclass(max_length: int = 150):
    """Prettify dataclasses.

    Prettify an existing dataclass by replacing __repr__ with a method that
    shortens variables to a max length, greatly reducing output for long strings
    in debug logs.
    """

    def _repr(self) -> str:
        def _format(value: Any) -> str:
            if isinstance(value, (str, bytes)):
                return _shorten(value, max_length)
            return value

        return (
            self.__class__.__name__
            + "("
            + ", ".join(
                [
                    f"{f}={_format(getattr(self, f))}"
                    for f in self.__dataclass_fields__.keys()
                ]
            )
            + ")"
        )

    def _wrap(cls):
        setattr(cls, "__repr__", _repr)
        return cls

    return _wrap


async def error_handler(func, fallback, *args, **kwargs):
    """Call a function and re-map exceptions to match pyatv interface."""
    try:
        return await func(*args, **kwargs)
    except (OSError, asyncio.TimeoutError) as ex:
        raise exceptions.ConnectionFailedError(str(ex)) from ex
    except (exceptions.BackOffError, exceptions.NoCredentialsError):
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


def _running_in_pyatv_repo() -> bool:
    """Return pyatv is run via pytest inside its own repo."""
    current_test = environ.get("PYTEST_CURRENT_TEST")
    if current_test:
        pyatv_path = path.dirname(path.dirname(pyatv.__file__))
        test_file = current_test.split("::")[0]
        abs_path = path.join(pyatv_path, test_file)
        return path.exists(abs_path)
    return False


# https://stackoverflow.com/questions/2536307/
#   decorators-in-the-python-standard-lib-deprecated-specifically
def deprecated(func):
    """Decorate functions that are deprecated."""
    if _running_in_pyatv_repo():
        return func

    @functools.wraps(func)
    def new_func(*args, **kwargs):
        # Tests typically call deprecated methods, yielding warnings. Suppress these
        # warnings when running tests with pytest.
        if not _running_in_pyatv_repo():
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


def shift_hex_identifier(identifier: str) -> str:
    """Repeatably modify a unique identifier to avoid collisions."""
    assert len(identifier) >= 2
    first, rest = identifier[:2], identifier[2:]
    shifted = f"{(int(first, 16) + 1) % 256:02x}"
    if identifier.isupper():
        shifted = shifted.upper()
    return shifted + rest





def stringify_model(model: BaseModel) -> Sequence[str]:
    """Recursively traverse a pydantic model and print values.

    This version no longer assumes that optional fields contain only basic types.
    If an optional field’s type annotation includes a BaseModel, then if a non-None
    value is present it will be recursed into. Otherwise, the field’s value and its
    annotated type (including that it is optional) are printed.
    """

    def _lookup_type(current_model: BaseModel, type_path: str) -> str:
        splitted_path = type_path.split(".", maxsplit=1)
        value = current_model.__annotations__[splitted_path[0]]
        if len(splitted_path) == 1:
            if value.__dict__.get("__origin__") is Union:
                return ", ".join(arg.__name__ for arg in value.__args__)
            return value.__name__
        return _lookup_type(value, splitted_path[1])

    def _recurse_into(current_model: BaseModel, prefix: str, output: List[str]) -> Sequence[str]:
        for name, field in dict(current_model).items():
            # If the field is itself a pydantic model, recurse into it.
            if hasattr(field, "__annotations__"):
                _recurse_into(getattr(current_model, name), f"{prefix or ''}{name}.", output)
            # Special handling for dictionaries: iterate over its items.
            elif isinstance(field, dict):
                for key, subvalue in field.items():
                    # If the value is a dict, iterate one level deeper.
                    if isinstance(subvalue, dict):
                        for inner_key, inner_value in subvalue.items():
                            output.append(
                                f"{prefix}{name}[\"{key}\"].{inner_key} = {repr(inner_value)}"
                            )
                    else:
                        output.append(
                            f"{prefix}{name}[\"{key}\"] = {repr(subvalue)}"
                        )
            # Handle Optional[BaseModel] fields.
            elif get_origin(field) is Union and get_args(field)[1] is not type(None):
                if getattr(current_model, name) is not None:
                    if (isinstance(current_model, BaseModel)):
                        _recurse_into(getattr(current_model, name), f"{prefix}{name}.", output)
                    output.append(f"{prefix}{name} = {repr(field)}")
                else:
                    field_type = _lookup_type(current_model, f"{prefix}{name}")
                    output.append(f"{prefix}{name} = {field} ({field_type})")
            else:
                output.append(f"{prefix}{name} = {repr(field)}")
        return output

    return _recurse_into(model, "", [])


def update_model_field(
    model: BaseModel, field: str, value: Union[str, int, float, None]
) -> None:
    """Update a field in a model using dotting string path."""
    splitted_path = field.split(".", maxsplit=1)
    next_field = splitted_path[0]

    if not hasattr(model, next_field):
        raise AttributeError(f"{model} has no field {next_field}")

    if len(splitted_path) > 1:
        update_model_field(getattr(model, next_field), splitted_path[1], value)
    else:
        model.parse_obj({field: value})
        setattr(model, field, value)
