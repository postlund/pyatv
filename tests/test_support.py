"""Unit tests for pyatv.support."""

import asyncio
import unittest
import logging
from unittest.mock import MagicMock

import asynctest

from pyatv import exceptions
from pyatv.support import error_handler, log_binary


class TestException(Exception):
    pass


async def doraise(exception):
    raise exception()


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


class SupporLogtTest(unittest.TestCase):

    def setUp(self):
        self.mock_logger = MagicMock()
        self.mock_logger.return_value = True

    def test_no_log_if_not_debug(self):
        self.mock_logger.isEnabledFor.return_value = False
        log_binary(self.mock_logger, 'test')
        self.mock_logger.isEnabledFor.assert_called_with(logging.DEBUG)

    def test_log_no_args_if_enabled(self):
        log_binary(self.mock_logger, 'testing')
        self.assertEqual(self._debug_string(), 'testing ()')

    def test_log_single_arg_if_enabled(self):
        log_binary(self.mock_logger, 'abc', test=b'\x01\x02')
        self.assertEqual(self._debug_string(), 'abc (test=0102)')

    def test_log_multiple_args_if_enabled(self):
        log_binary(self.mock_logger, 'k', test=b'\x01\x02', dummy=b'\xfe')
        self.assertEqual(self._debug_string(), 'k (dummy=fe, test=0102)')

    # This method generates the formatted debug string
    def _debug_string(self):
        call_args = self.mock_logger.debug.call_args[0]
        formatting = call_args[0]
        args = call_args[1:]
        return formatting % args
