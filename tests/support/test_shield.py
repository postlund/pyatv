"""Unit tests for pyatv.support.shield."""

import pytest

from pyatv.exceptions import BlockedStateError, InvalidStateError
from pyatv.support import shield


class Dummy:
    pass


def test_shield_object():
    obj = Dummy()

    assert not shield.is_shielded(obj)
    obj2 = shield.shield(obj)
    assert obj == obj2
    assert shield.is_shielded(obj)


def test_cannot_block_unshielded_object():
    obj = Dummy()
    with pytest.raises(InvalidStateError):
        shield.block(obj)


def test_is_blocking_does_not_raise_on_unshielded_object():
    obj = Dummy()
    assert not shield.is_blocking(obj)


def test_block_shielded_object():
    obj = Dummy()
    shield.shield(obj)
    assert not shield.is_blocking(obj)
    shield.block(obj)
    assert shield.is_blocking(obj)


class GuardedClass:
    @shield.guard
    def guarded_method(self, a):
        return a * a

    def unguarded_method(self, b):
        return b + b


def test_guarded_methods():
    obj = GuardedClass()

    shield.shield(obj)

    # Should work fine since object is not blocked
    assert obj.guarded_method(2) == 4
    assert obj.unguarded_method(4) == 8

    shield.block(obj)

    with pytest.raises(BlockedStateError):
        obj.guarded_method()

    obj.unguarded_method(5) == 10
