"""Functional tests for helper methods. Agnostic to protocol implementation."""

import asynctest

from asynctest.mock import patch

from pyatv import (conf, helpers)


class MockAppleTV:
    """Used to mock a device."""

    async def logout(self):
        """Fake logout method."""
        pass


class HelpersTest(asynctest.TestCase):

    def setUp(self):
        self.config = conf.AppleTV('address', 'name')
        self.mock_device = asynctest.mock.Mock(MockAppleTV())

    @patch('pyatv.scan', return_value=[])
    def test_auto_connect_with_no_device(self, scan_func):
        self.device_found = True

        async def found_handler():
            self.assertTrue(False, msg='should not be called')

        async def not_found_handler():
            self.device_found = False

        helpers.auto_connect(found_handler,
                             not_found=not_found_handler)

        self.assertFalse(self.device_found)

    @patch('pyatv.scan')
    @patch('pyatv.connect')
    def test_auto_connect_with_device(self, connect_func, scan_func):
        scan_func.return_value = [self.config]
        connect_func.return_value = self.mock_device

        self.found_device = None

        async def found_handler(atv):
            self.found_device = atv

        helpers.auto_connect(found_handler)

        self.assertEqual(self.found_device, self.mock_device)
        self.assertTrue(self.mock_device.logout.called)
