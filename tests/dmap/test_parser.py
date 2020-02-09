"""Unit tests for pyatv.dmap.parser."""

import unittest
import plistlib

from pyatv import exceptions
from pyatv.dmap import (tags, parser)

TEST_TAGS = {
    'uuu8': parser.DmapTag(tags.read_uint, 'uint8'),
    'uu16': parser.DmapTag(tags.read_uint, 'uint16'),
    'uu32': parser.DmapTag(tags.read_uint, 'uint32'),
    'uu64': parser.DmapTag(tags.read_uint, 'uint64'),
    'bola': parser.DmapTag(tags.read_bool, 'bool'),
    'bolb': parser.DmapTag(tags.read_bool, 'bool'),
    'stra': parser.DmapTag(tags.read_str, 'string'),
    'strb': parser.DmapTag(tags.read_str, 'string'),
    'cona': parser.DmapTag('container', 'container'),
    'conb': parser.DmapTag('container', 'container 2'),
    'igno': parser.DmapTag(tags.read_ignore, 'ignore'),
    'plst': parser.DmapTag(tags.read_bplist, 'bplist'),
    'byte': parser.DmapTag(tags.read_bytes, 'bytes'),
}


def lookup_tag(name):
    return TEST_TAGS[name]


class ParserTest(unittest.TestCase):

    def test_parse_uint_of_various_lengths(self):
        in_data = tags.uint8_tag('uuu8', 12) + \
                  tags.uint16_tag('uu16', 37888) + \
                  tags.uint32_tag('uu32', 305419896) + \
                  tags.uint64_tag('uu64', 8982983289232)
        parsed = parser.parse(in_data, lookup_tag)
        self.assertEqual(4, len(parsed))
        self.assertEqual(12, parser.first(parsed, 'uuu8'))
        self.assertEqual(37888, parser.first(parsed, 'uu16'))
        self.assertEqual(305419896, parser.first(parsed, 'uu32'))
        self.assertEqual(8982983289232, parser.first(parsed, 'uu64'))

    def test_parse_bool(self):
        in_data = tags.bool_tag('bola', True) + \
                  tags.bool_tag('bolb', False)
        parsed = parser.parse(in_data, lookup_tag)
        self.assertEqual(2, len(parsed))
        self.assertTrue(parser.first(parsed, 'bola'))
        self.assertFalse(parser.first(parsed, 'bolb'))

    def test_parse_strings(self):
        in_data = tags.string_tag('stra', '') + \
                  tags.string_tag('strb', 'test string')
        parsed = parser.parse(in_data, lookup_tag)
        self.assertEqual(2, len(parsed))
        self.assertEqual('', parser.first(parsed, 'stra'))
        self.assertEqual('test string', parser.first(parsed, 'strb'))

    def test_parse_binary_plist(self):
        data = {"key": "value"}
        in_data = tags.raw_tag(
            'plst', plistlib.dumps(data, fmt=plistlib.FMT_BINARY))
        parsed = parser.parse(in_data, lookup_tag)
        self.assertEqual(1, len(parsed))
        self.assertEqual(data, parser.first(parsed, 'plst'))

    def test_parse_bytes(self):
        in_data = tags.raw_tag('byte', b'\x01\xAA\xFF\x45')
        parsed = parser.parse(in_data, lookup_tag)
        self.assertEqual(1, len(parsed))
        self.assertEqual('0x01aaff45', parser.first(parsed, 'byte'))

    def test_parse_value_in_container(self):
        in_data = tags.container_tag('cona',
                                     tags.uint8_tag('uuu8', 36) +
                                     tags.uint16_tag('uu16', 13000))
        parsed = parser.parse(in_data, lookup_tag)
        self.assertEqual(1, len(parsed))
        inner = parser.first(parsed, 'cona')
        self.assertEqual(2, len(inner))
        self.assertEqual(36, parser.first(inner, 'uuu8'))
        self.assertEqual(13000, parser.first(inner, 'uu16'))

    def test_extract_simplified_container(self):
        elem = tags.uint8_tag('uuu8', 12)
        inner = tags.container_tag('conb', elem)
        in_data = tags.container_tag('cona', inner)
        parsed = parser.parse(in_data, lookup_tag)
        self.assertEqual(12, parser.first(parsed, 'cona', 'conb', 'uuu8'))

    def test_ignore_value(self):
        elem = tags.uint8_tag('igno', 44)
        parsed = parser.parse(elem, lookup_tag)
        self.assertEqual(parser.first(parsed, 'igno'), None)

    def test_simple_pprint(self):
        elem = tags.uint8_tag('uuu8', 12)
        inner = tags.container_tag('conb', elem)
        in_data = tags.container_tag('cona', inner)
        parsed = parser.parse(in_data, lookup_tag)
        self.assertEqual(parser.pprint(parsed, lookup_tag),
                         'cona: [container, container]\n' +
                         '  conb: [container, container 2]\n' +
                         '    uuu8: 12 [uint, uint8]\n')

    def test_print_invalid_input_raises_exception(self):
        with self.assertRaises(exceptions.InvalidDmapDataError):
            parser.pprint('bad data', lookup_tag)
