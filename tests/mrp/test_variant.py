"""Unit tests for pyatv.mrp.variant."""

import unittest

from pyatv.mrp.variant import (read_variant, write_variant)


class VariantTest(unittest.TestCase):

    def test_read_single_byte(self):
        self.assertEqual(read_variant(b'\x00')[0], 0x00)
        self.assertEqual(read_variant(b'\x35')[0], 0x35)

    def test_read_multiple_bytes(self):
        self.assertEqual(read_variant(b'\xb5\x44')[0], 8757)
        self.assertEqual(read_variant(b'\xc5\x92\x01')[0], 18757)

    def test_read_and_return_remaining_data(self):
        value, remaining = read_variant(b'\xb5\x44\xca\xfe')
        self.assertEqual(value, 8757)
        self.assertEqual(remaining, b'\xca\xfe')

    def test_read_invalid_variant(self):
        with self.assertRaises(Exception):
            read_variant(b'\x80')

    def test_write_single_byte(self):
        self.assertEqual(write_variant(0x00), b'\x00')
        self.assertEqual(write_variant(0x35), b'\x35')

    def test_write_multiple_bytes(self):
        self.assertEqual(write_variant(8757), b'\xb5\x44')
        self.assertEqual(write_variant(18757), b'\xc5\x92\x01')
