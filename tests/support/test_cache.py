"""Unit tests for cache."""

import pytest

from pyatv.support.cache import Cache

ID1 = "id1"
ID2 = "id2"
ID3 = "id3"
DATA1 = 123
DATA2 = 456
DATA3 = 789


@pytest.fixture
def cache():
    yield Cache(limit=2)


def test_cache_is_empty(cache):
    assert cache.empty()


def test_put_get_item(cache):
    cache.put(ID1, DATA1)
    assert cache.get(ID1) == DATA1


def test_put_get_multiple(cache):
    cache.put(ID1, DATA1)
    cache.put(ID2, DATA2)

    assert cache.get(ID1) == DATA1
    assert cache.get(ID2) == DATA2


def test_cache_not_empty(cache):
    cache.put(ID1, DATA1)
    assert not cache.empty()


def test_cache_has_item(cache):
    cache.put(ID1, DATA1)

    assert ID1 in cache
    assert ID2 not in cache


def test_cache_size(cache):
    assert len(cache) == 0
    cache.put(ID1, DATA1)
    assert len(cache) == 1


def test_put_same_identifier_replaces_data(cache):
    cache.put(ID1, DATA1)
    cache.put(ID1, DATA2)
    assert cache.get(ID1) == DATA2
    assert len(cache) == 1


def test_put_removes_oldest(cache):
    cache.put(ID1, DATA1)
    cache.put(ID2, DATA2)
    cache.put(ID3, DATA3)

    assert len(cache) == 2
    assert ID1 not in cache
    assert ID2 in cache
    assert ID3 in cache


def test_get_makes_data_newer(cache):
    cache.put(ID1, DATA1)
    cache.put(ID2, DATA2)
    cache.get(ID1)
    cache.put(ID3, DATA3)

    assert len(cache) == 2
    assert ID1 in cache
    assert ID2 not in cache
    assert ID3 in cache


def test_get_latest_identifier(cache):
    assert cache.latest() is None

    cache.put(ID1, DATA1)
    assert cache.latest() == ID1

    cache.put(ID2, DATA2)
    assert cache.latest() == ID2

    cache.get(ID1)
    assert cache.latest() == ID1
