"""Support functions used in library."""

import asyncio
import binascii
import functools
import logging
from os import environ, path
from typing import Any, List, Union, get_args, get_origin
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


def stringify_model(model: BaseModel) -> List[str]:
    """Recursively traverse BaseModel to produce a list of strings describing fields.

    - For nested BaseModels, the function recurses.
    - For dictionary fields, it recursively iterates over keys and nested values.
    - If a field’s annotation is a Union (e.g. Optional[...]), all constituent
    type names are shown.
    """

    def lookup_type(annotation: Any, value: Any) -> str:
        """Return a string representation for a type annotation."""
        origin = get_origin(annotation)

        if origin is Union:
            args = get_args(annotation)
            types = []
            for arg in args:
                if arg is not None:
                    types.append(getattr(arg, "__name__", str(arg)))
                elif value is None:
                    types.append("None")
            if len(types) == 1:
                return types[0]
            return ", ".join(getattr(arg, "__name__", str(arg)) for arg in args)
        return getattr(annotation, "__name__", str(annotation))

    def recurse(instance: Any, prefix: str = "") -> List[str]:
        """Recursively traverse a BaseModel (or dict).

        and collect string representations.
        """
        lines: List[str] = []
        if isinstance(instance, BaseModel):
            # Retrieve annotations from the model.
            annotations = instance.__annotations__
            for field_name, field_value in instance.__dict__.items():
                # Build the full field name with current prefix.
                full_field_name = f"{prefix}{field_name}"
                # If the field is another BaseModel, recurse into it.
                if isinstance(field_value, BaseModel):
                    lines.extend(recurse(field_value, full_field_name + "."))
                # If the field is a dictionary, delegate to process_dict.
                elif isinstance(field_value, dict):
                    lines.extend(process_dict(field_value, full_field_name))
                else:
                    # Look up the annotated type; if missing,
                    # fall back on the runtime type.
                    annotation = annotations.get(field_name, type(field_value))
                    type_str = lookup_type(annotation, field_value)
                    lines.append(f"{full_field_name} = {field_value} ({type_str})")
        else:
            # If the instance is not a BaseModel, output its repr and type.
            lines.append(f"{prefix} = {repr(instance)} ({type(instance).__name__})")
        return lines

    def process_dict(d: dict, prefix: str) -> List[str]:
        """Recursively process a dictionary field."""
        lines: List[str] = []
        for key, value in d.items():
            # Use repr(key) to account for keys that are strings, numbers, etc.
            full_field_name = f"{prefix}[{repr(key)}]"
            if isinstance(value, dict):
                lines.extend(process_dict(value, full_field_name))
            elif isinstance(value, BaseModel):
                lines.extend(recurse(value, full_field_name + "."))
            else:
                lines.append(
                    f"{full_field_name} = {repr(value)} ({type(value).__name__})"
                )
        return lines

    return recurse(model, "")


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
