"""Unit tests for pyatv.support.collections"""
import typing
from unittest.mock import sentinel

import pytest

from pyatv.support.collections import CaseInsensitiveDict, dict_merge

# CaseInsentitiveDict


@pytest.fixture
def fixture_dict():
    ret = CaseInsensitiveDict()
    ret["foo"] = sentinel.foo
    return ret


@pytest.fixture(params=["foo", "FOO", "Foo", "fOO"])
def key(request):
    return request.param


@pytest.fixture(params=["bar", "BAR", "Bar", "bAR"])
def new_key(request):
    return request.param


def test_getitem(fixture_dict: CaseInsensitiveDict, key: str):
    assert fixture_dict[key] == sentinel.foo


def test_setitem(fixture_dict: CaseInsensitiveDict, key: str, new_key: str):
    fixture_dict[key] = sentinel.Foo
    assert fixture_dict[key] != sentinel.foo
    assert fixture_dict[key] == sentinel.Foo
    assert len(fixture_dict) == 1
    fixture_dict[new_key] = getattr(sentinel, new_key)
    fixture_dict["bar"] = getattr(sentinel, new_key)
    assert len(fixture_dict) == 2


def test_delitem(fixture_dict: CaseInsensitiveDict, key: str):
    del fixture_dict[key]
    assert len(fixture_dict) == 0
    with pytest.raises(KeyError):
        fixture_dict["foo"]


def test_contains(fixture_dict: CaseInsensitiveDict, key: str):
    assert key in fixture_dict


def test_equals_case_insensitive(fixture_dict: CaseInsensitiveDict):
    other = CaseInsensitiveDict()
    other["FOO"] = sentinel.foo
    assert fixture_dict == other


def test_equals_plain_dict(fixture_dict: CaseInsensitiveDict):
    other = {"Foo": sentinel.foo}
    assert fixture_dict == other


def test_init_mapping():
    cid = CaseInsensitiveDict({"FOO": sentinel.FOO, "bAr": sentinel.bAr})
    assert cid["foo"] == sentinel.FOO
    assert cid["bar"] == sentinel.bAr
    assert len(cid) == 2


def test_init_iterable():
    cid = CaseInsensitiveDict([("fOO", sentinel.fOO), ("BaR", sentinel.BaR)])
    assert cid["foo"] == sentinel.fOO
    assert cid["bar"] == sentinel.BaR
    assert len(cid) == 2


def test_init_kwargs():
    cid = CaseInsensitiveDict({"FOO": sentinel.FOO, "bAr": sentinel.bAr})
    cid = CaseInsensitiveDict(foO=sentinel.foO, BAR=sentinel.BAR)
    assert cid["foo"] == sentinel.foO
    assert cid["bar"] == sentinel.BAR
    assert len(cid) == 2


# dict_merge


@pytest.mark.parametrize(
    "dict_a,dict_b,expected",
    [
        ({"a": 1}, {}, {"a": 1}),
        ({}, {"a": 1}, {"a": 1}),
        ({"a": 1}, {"a": 2}, {"a": 1}),
    ],
)
def test_dict_merge(dict_a, dict_b, expected):
    assert dict_merge(dict_a, dict_b) == expected


def test_dict_merge_returns_dict_a():
    dict_a = {"a": 1}
    dict_b = {"b": 2}
    merged = dict_merge(dict_a, dict_b)
    assert merged is dict_a
