"""Unit tests for pyatv.dmap."""

import unittest

from pyatv import (tags, dmap, exceptions)

TEST_TAGS = {
    'uuu8': dmap.DmapTag(tags.read_uint, 'uint8'),
    'uu16': dmap.DmapTag(tags.read_uint, 'uint16'),
    'uu32': dmap.DmapTag(tags.read_uint, 'uint32'),
    'uu64': dmap.DmapTag(tags.read_uint, 'uint64'),
    'bola': dmap.DmapTag(tags.read_bool, 'bool'),
    'bolb': dmap.DmapTag(tags.read_bool, 'bool'),
    'stra': dmap.DmapTag(tags.read_str, 'string'),
    'strb': dmap.DmapTag(tags.read_str, 'string'),
    'rawa': dmap.DmapTag(tags.read_raw, 'raw'),
    'cona': dmap.DmapTag('container', 'container'),
    'conb': dmap.DmapTag('container', 'container 2'),
    'igno': dmap.DmapTag(tags.read_ignore, 'ignore'),
}


def lookup_tag(name):
    return TEST_TAGS[name]


class DmapTest(unittest.TestCase):

    def test_parse_uint_of_various_lengths(self):
        in_data = tags.uint8_tag('uuu8', 12) + \
                  tags.uint16_tag('uu16', 37888) + \
                  tags.uint32_tag('uu32', 305419896) + \
                  tags.uint64_tag('uu64', 8982983289232)
        parsed = dmap.parse(in_data, lookup_tag)
        self.assertEqual(4, len(parsed))
        self.assertEqual(12, dmap.first(parsed, 'uuu8'))
        self.assertEqual(37888, dmap.first(parsed, 'uu16'))
        self.assertEqual(305419896, dmap.first(parsed, 'uu32'))
        self.assertEqual(8982983289232, dmap.first(parsed, 'uu64'))

    def test_parse_bool(self):
        in_data = tags.bool_tag('bola', True) + \
                  tags.bool_tag('bolb', False)
        parsed = dmap.parse(in_data, lookup_tag)
        self.assertEqual(2, len(parsed))
        self.assertTrue(dmap.first(parsed, 'bola'))
        self.assertFalse(dmap.first(parsed, 'bolb'))

    def test_parse_strings(self):
        in_data = tags.string_tag('stra', '') + \
                  tags.string_tag('strb', 'test string')
        parsed = dmap.parse(in_data, lookup_tag)
        self.assertEqual(2, len(parsed))
        self.assertEqual('', dmap.first(parsed, 'stra'))
        self.assertEqual('test string', dmap.first(parsed, 'strb'))

    def test_parse_raw_data(self):
        in_data = tags.raw_tag('rawa', b'\x01\x02\x03')
        parsed = dmap.parse(in_data, lookup_tag)
        self.assertEqual(1, len(parsed))
        self.assertEqual(b'\x01\x02\x03', dmap.first(parsed, 'rawa'))

    def test_parse_value_in_container(self):
        in_data = tags.container_tag('cona',
                                     tags.uint8_tag('uuu8', 36) +
                                     tags.uint16_tag('uu16', 13000))
        parsed = dmap.parse(in_data, lookup_tag)
        self.assertEqual(1, len(parsed))
        inner = dmap.first(parsed, 'cona')
        self.assertEqual(2, len(inner))
        self.assertEqual(36, dmap.first(inner, 'uuu8'))
        self.assertEqual(13000, dmap.first(inner, 'uu16'))

    def test_extract_simplified_container(self):
        elem = tags.uint8_tag('uuu8', 12)
        inner = tags.container_tag('conb', elem)
        in_data = tags.container_tag('cona', inner)
        parsed = dmap.parse(in_data, lookup_tag)
        self.assertEqual(12, dmap.first(parsed, 'cona', 'conb', 'uuu8'))

    def test_ignore_value(self):
        elem = tags.uint8_tag('igno', 44)
        parsed = dmap.parse(elem, lookup_tag)
        self.assertEqual(dmap.first(parsed, 'igno'), None)

    def test_simple_pprint(self):
        elem = tags.uint8_tag('uuu8', 12)
        inner = tags.container_tag('conb', elem)
        in_data = tags.container_tag('cona', inner)
        parsed = dmap.parse(in_data, lookup_tag)
        self.assertEqual(dmap.pprint(parsed, lookup_tag),
                         'cona: [container, container]\n' +
                         '  conb: [container, container 2]\n' +
                         '    uuu8: 12 [uint, uint8]\n')

    def test_print_invalid_input_raises_exception(self):
        with self.assertRaises(exceptions.InvalidDmapDataError):
            dmap.pprint('bad data', lookup_tag)
