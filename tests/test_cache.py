"""Unit tests for cache."""

import unittest

from pyatv.cache import Cache

ID1 = 'id1'
ID2 = 'id2'
ID3 = 'id3'
DATA1 = 123
DATA2 = 456
DATA3 = 789


class CacheTest(unittest.TestCase):

    def setUp(self):
        self.cache = Cache(limit=2)

    def test_cache_is_empty(self):
        self.assertTrue(self.cache.empty())

    def test_put_get_item(self):
        self.cache.put(ID1, DATA1)
        self.assertEqual(self.cache.get(ID1), DATA1)

    def test_put_get_multiple(self):
        self.cache.put(ID1, DATA1)
        self.cache.put(ID2, DATA2)

        self.assertEqual(self.cache.get(ID1), DATA1)
        self.assertEqual(self.cache.get(ID2), DATA2)

    def test_cache_not_empty(self):
        self.cache.put(ID1, DATA1)
        self.assertFalse(self.cache.empty())

    def test_cache_has_item(self):
        self.cache.put(ID1, DATA1)

        self.assertTrue(ID1 in self.cache)
        self.assertFalse(ID2 in self.cache)

    def test_cache_size(self):
        self.assertEqual(len(self.cache), 0)
        self.cache.put(ID1, DATA1)
        self.assertEqual(len(self.cache), 1)

    def test_put_same_identifier_replaces_data(self):
        self.cache.put(ID1, DATA1)
        self.cache.put(ID1, DATA2)
        self.assertEqual(self.cache.get(ID1), DATA2)
        self.assertEqual(len(self.cache), 1)

    def test_put_removes_oldest(self):
        self.cache.put(ID1, DATA1)
        self.cache.put(ID2, DATA2)
        self.cache.put(ID3, DATA3)

        self.assertEqual(len(self.cache), 2)
        self.assertNotIn(ID1, self.cache)
        self.assertIn(ID2, self.cache)
        self.assertIn(ID3, self.cache)

    def test_get_makes_data_newer(self):
        self.cache.put(ID1, DATA1)
        self.cache.put(ID2, DATA2)
        self.cache.get(ID1)
        self.cache.put(ID3, DATA3)

        self.assertEqual(len(self.cache), 2)
        self.assertIn(ID1, self.cache)
        self.assertNotIn(ID2, self.cache)
        self.assertIn(ID3, self.cache)

    def test_get_latest_identifier(self):
        self.assertEqual(self.cache.latest(), None)

        self.cache.put(ID1, DATA1)
        self.assertEqual(self.cache.latest(), ID1)

        self.cache.put(ID2, DATA2)
        self.assertEqual(self.cache.latest(), ID2)

        self.cache.get(ID1)
        self.assertEqual(self.cache.latest(), ID1)
