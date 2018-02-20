"""Unit tests for pyatv.log."""

import unittest
import logging
from unittest.mock import MagicMock

from pyatv import log


class LogTest(unittest.TestCase):

    def setUp(self):
        self.mock_logger = MagicMock()
        self.mock_logger.return_value = True

    def test_no_log_if_not_debug(self):
        self.mock_logger.isEnabledFor.return_value = False
        log.log_binary(self.mock_logger, 'test')
        self.mock_logger.isEnabledFor.assert_called_with(logging.DEBUG)

    def test_log_no_args_if_enabled(self):
        log.log_binary(self.mock_logger, 'testing')
        self.assertEqual(self._debug_string(), 'testing ()')

    def test_log_single_arg_if_enabled(self):
        log.log_binary(self.mock_logger, 'abc', test=b'\x01\x02')
        self.assertEqual(self._debug_string(), 'abc (test=0102)')

    def test_log_multiple_args_if_enabled(self):
        log.log_binary(self.mock_logger, 'k', test=b'\x01\x02', dummy=b'\xfe')
        self.assertEqual(self._debug_string(), 'k (dummy=fe, test=0102)')

    # This method generates the formatted debug string
    def _debug_string(self):
        call_args = self.mock_logger.debug.call_args[0]
        formatting = call_args[0]
        args = call_args[1:]
        return formatting % args
