"""Functional tests for helper methods. Agnostic to protocol implementation."""

import asyncio
import asynctest

from asynctest.mock import patch

from pyatv import (AppleTVDevice, helpers)


class MockAppleTV:
    """Used to mock a device."""

    @asyncio.coroutine
    def logout(self):
        """Fake logout method."""
        pass


class HelpersTest(asynctest.TestCase):

    def setUp(self):
        self.device_details = AppleTVDevice('name', 'address', 'hsgid')
        self.mock_device = asynctest.mock.Mock(MockAppleTV())

    @patch('pyatv.scan_for_apple_tvs', return_value=[])
    def test_auto_connect_with_no_device(self, scan_func):
        self.device_found = True

        @asyncio.coroutine
        def found_handler():
            self.assertTrue(False, msg='should not be called')

        @asyncio.coroutine
        def not_found_handler():
            self.device_found = False

        helpers.auto_connect(found_handler,
                             not_found=not_found_handler,
                             event_loop=self.loop)

        self.assertFalse(self.device_found)

    @patch('pyatv.scan_for_apple_tvs')
    @patch('pyatv.connect_to_apple_tv')
    def test_auto_connect_with_device(self, connect_func, scan_func):
        scan_func.return_value = [self.device_details]
        connect_func.return_value = self.mock_device

        self.found_device = None

        @asyncio.coroutine
        def found_handler(atv):
            self.found_device = atv

        helpers.auto_connect(found_handler,
                             event_loop=self.loop)

        self.assertEqual(self.found_device, self.mock_device)
        self.assertTrue(self.mock_device.logout.called)
