"""Unit tests for pyatv.support."""

import os
import asyncio
import unittest
import logging
from unittest.mock import MagicMock, patch

import asynctest

from pyatv import exceptions
from pyatv.support import error_handler, log_binary, log_protobuf
from pyatv.mrp.protobuf import ProtocolMessage


class TestException(Exception):
    pass


async def doraise(exception):
    raise exception()


# This method generates the formatted debug string
def _debug_string(logger):
    call_args = logger.debug.call_args[0]
    formatting = call_args[0]
    args = call_args[1:]
    return formatting % args


class SupporErrorHandlerTest(asynctest.TestCase):

    async def test_return_value(self):
        async def _returns():
            return 123

        self.assertEqual(
            await error_handler(_returns, TestException), 123)

    async def test_oserror(self):
        with self.assertRaises(exceptions.ConnectionFailedError):
            await error_handler(doraise, TestException, OSError)

    async def test_timeout(self):
        with self.assertRaises(exceptions.ConnectionFailedError):
            await error_handler(
                doraise, TestException, asyncio.TimeoutError)

    async def test_backoff(self):
        with self.assertRaises(exceptions.BackOffError):
            await error_handler(
                doraise, TestException, exceptions.BackOffError)

    async def test_no_credentials(self):
        with self.assertRaises(exceptions.NoCredentialsError):
            await error_handler(
                doraise, TestException, exceptions.NoCredentialsError)

    async def test_other_exception(self):
        with self.assertRaises(TestException):
            await error_handler(doraise, TestException, Exception)


class SupporLogBinaryTest(unittest.TestCase):

    def setUp(self):
        self.logger = MagicMock()
        self.logger.return_value = True

    def test_no_log_if_not_debug(self):
        self.logger.isEnabledFor.return_value = False
        log_binary(self.logger, 'test')
        self.logger.isEnabledFor.assert_called_with(logging.DEBUG)

    def test_log_no_args_if_enabled(self):
        log_binary(self.logger, 'testing')
        self.assertEqual(_debug_string(self.logger), 'testing ()')

    def test_log_single_arg_if_enabled(self):
        log_binary(self.logger, 'abc', test=b'\x01\x02')
        self.assertEqual(_debug_string(self.logger), 'abc (test=0102)')

    def test_log_multiple_args_if_enabled(self):
        log_binary(self.logger, 'k', test=b'\x01\x02', dummy=b'\xfe')
        self.assertEqual(_debug_string(self.logger), 'k (dummy=fe, test=0102)')

    def test_log_limit_output(self):
        log_binary(self.logger, 'msg', a=b'\x01' * 1024, b=b'\x02' * 1024)

        # Output will become:
        # msg (a=, b=)
        # Which is length 12. Then add 2 * 512 for limit = 1036
        self.assertEqual(len(_debug_string(self.logger)), 1036)

    @patch.dict(os.environ, {"PYATV_BINARY_MAX_LINE": "5"})
    def test_log_with_length_override(self):
        log_binary(self.logger, 'msg', a=b'\x01' * 20, b=b'\x02' * 20)
        self.assertEqual(_debug_string(self.logger), 'msg (a=01..., b=02...)')


class SupportLogProtobufTest(unittest.TestCase):

    def setUp(self):
        self.logger = MagicMock()
        self.logger.return_value = True

        self.msg = ProtocolMessage()
        self.msg.identifier = "aaaaaaaaaa"

    def test_no_log_if_not_debug(self):
        self.logger.isEnabledFor.return_value = False
        log_protobuf(self.logger, "test", self.msg)
        self.logger.isEnabledFor.assert_called_with(logging.DEBUG)

    def test_log_message(self):
        log_protobuf(self.logger, "test", self.msg)
        self.assertEqual(_debug_string(self.logger),
                         'test: identifier: "aaaaaaaaaa"')

    def test_log_limit_message_max_length(self):
        self.msg.identifier = "a" * 200
        log_protobuf(self.logger, "test", self.msg)
        self.assertEqual(len(_debug_string(self.logger)), 156)

    @patch.dict(os.environ, {"PYATV_PROTOBUF_MAX_LINE": "5"})
    def test_log_with_length_override(self):
        log_protobuf(self.logger, "text", self.msg)
        self.assertEqual(_debug_string(self.logger), 'text: id...')
