"""Unit tests for pyatv.support."""

import asyncio
import logging
import math
import os
from unittest.mock import MagicMock, patch

import pytest

from pyatv import exceptions
from pyatv.protocols.mrp.protobuf import ProtocolMessage
from pyatv.support import error_handler, log_binary, log_protobuf, map_range


class DummyException(Exception):
    pass


@pytest.fixture(name="logger")
def logger_fixture():
    logger = MagicMock()
    logger.return_value = True
    yield logger


@pytest.fixture
def message():
    msg = ProtocolMessage()
    msg.identifier = "aaaaaaaaaa"
    yield msg


async def doraise(exception):
    raise exception()


# This method generates the formatted debug string
def _debug_string(logger):
    call_args = logger.debug.call_args[0]
    formatting = call_args[0]
    args = call_args[1:]
    return formatting % args


async def test_error_handler_return_value():
    async def _returns():
        return 123

    assert await error_handler(_returns, DummyException) == 123


async def test_error_handleroserror():
    with pytest.raises(exceptions.ConnectionFailedError):
        await error_handler(doraise, DummyException, OSError)


async def test_error_handler_timeout():
    with pytest.raises(exceptions.ConnectionFailedError):
        await error_handler(doraise, DummyException, asyncio.TimeoutError)


async def test_error_handler_backoff():
    with pytest.raises(exceptions.BackOffError):
        await error_handler(doraise, DummyException, exceptions.BackOffError)


async def test_error_handler_no_credentials():
    with pytest.raises(exceptions.NoCredentialsError):
        await error_handler(doraise, DummyException, exceptions.NoCredentialsError)


async def test_error_handler_other_exception():
    with pytest.raises(DummyException):
        await error_handler(doraise, DummyException, Exception)


def test_log_binary_no_log_if_not_debug(logger):
    logger.isEnabledFor.return_value = False
    log_binary(logger, "test")
    logger.isEnabledFor.assert_called_with(logging.DEBUG)


def test_log_binary_no_log_if_not_custom_level(logger):
    logger.isEnabledFor.return_value = False
    log_binary(logger, "test", level=logging.INFO)
    logger.isEnabledFor.assert_called_with(logging.INFO)


def test_log_binary_log_no_args_if_enabled(logger):
    log_binary(logger, "testing")
    assert _debug_string(logger) == "testing ()"


def test_log_binary_log_empty_value_if_enabled(logger):
    log_binary(logger, "testing", test=None)
    assert _debug_string(logger) == "testing (test=)"


def test_log_binary_log_single_arg_if_enabled(logger):
    log_binary(logger, "abc", test=b"\x01\x02")
    assert _debug_string(logger) == "abc (test=0102)"


def test_log_binary_log_multiple_args_if_enabled(logger):
    log_binary(logger, "k", test=b"\x01\x02", dummy=b"\xfe")
    assert _debug_string(logger) == "k (dummy=fe, test=0102)"


def test_log_binary_log_limit_output(logger):
    log_binary(logger, "msg", a=b"\x01" * 1024, b=b"\x02" * 1024)

    # Output will become:
    # msg (a=, b=)
    # Which is length 12. Then add 2 * 512 for limit = 1036
    assert len(_debug_string(logger)) == 1036


def test_log_binary_non_bytes_as_string(logger):
    log_binary(logger, "msg", a=b"\x01", b=123, c="test")

    assert _debug_string(logger) == "msg (a=01, b=123, c=test)"


def test_protobuf_no_log_if_not_debug(logger, message):
    logger.isEnabledFor.return_value = False
    log_protobuf(logger, "test", message)
    logger.isEnabledFor.assert_called_with(logging.DEBUG)


def test_protobuf_log_message(logger, message):
    log_protobuf(logger, "test", message)
    assert _debug_string(logger) == 'test: identifier: "aaaaaaaaaa"'


def test_protobuf_log_limit_message_max_length(logger, message):
    message.identifier = "a" * 200
    log_protobuf(logger, "test", message)
    assert len(_debug_string(logger)) == 156


@patch.dict(os.environ, {"PYATV_PROTOBUF_MAX_LINE": "5"})
def test_protobuf_log_with_length_override(logger, message):
    log_protobuf(logger, "text", message)
    assert _debug_string(logger) == "text: id..."


def test_map_range():
    assert math.isclose(map_range(1.0, 0.0, 25.0, 0.0, 100.0), 4.0)


@pytest.mark.parametrize(
    "in_min,in_max,out_min,out_max",
    [
        # Bad in-ranges
        (0.0, 0.0, 0.0, 1.0),
        (1.0, 0.0, 0.0, 1.0),
        # Bad out-ranges
        (0.0, 1.0, 0.0, 0.0),
        (0.0, 1.0, 1.0, 0.0),
    ],
)
def test_map_range_bad_ranges(in_min, in_max, out_min, out_max):
    with pytest.raises(ValueError):
        map_range(1, in_min, in_max, out_min, out_max)


@pytest.mark.parametrize("value", [-1.0, 11.0])
def test_map_range_bad_input_values(value):
    with pytest.raises(ValueError):
        map_range(value, 0.0, 10.0, 20.0, 30.0)
