"""Unit tests for device_info."""

import unittest

from pyatv.const import DeviceModel
from pyatv.device_info import lookup_model, lookup_version


class DeviceInfoTest(unittest.TestCase):

    def test_lookup_existing_model(self):
        self.assertEqual(
            lookup_model('AppleTV6,2'), DeviceModel.Gen4K)

    def test_lookup_missing_model(self):
        self.assertEqual(
            lookup_model('bad_model'), DeviceModel.Unknown)

    def test_lookup_existing_version(self):
        self.assertEqual(lookup_version('17J586'), '13.0')

    def test_lookup_bad_version(self):
        self.assertIsNone(lookup_version(None))
        self.assertIsNone(lookup_version('bad_version'))

    def test_lookup_guess_major_version(self):
        self.assertEqual(lookup_version('16F123'), '12.x')
        self.assertEqual(lookup_version('17F123'), '13.x')
