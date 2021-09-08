"""Unit tests for pyatv.protocols.raop.fifo."""

import pytest

from pyatv.protocols.raop.fifo import PacketFifo


def test_add_to_fifo():
    fifo = PacketFifo(10)
    assert not fifo

    fifo[123] = 456
    assert len(fifo) == 1
    assert fifo


def test_add_existing_to_fifo():
    fifo = PacketFifo(10)
    fifo[123] = 456

    with pytest.raises(ValueError):
        fifo[123] = 789


def test_add_index_not_int_raises():
    fifo = PacketFifo(10)

    with pytest.raises(TypeError):
        fifo["test"] = 123


def test_get_missing_from_fifo():
    fifo = PacketFifo(10)

    with pytest.raises(KeyError):
        fifo[123]


def test_get_index_not_int_raises():
    fifo = PacketFifo(10)

    with pytest.raises(TypeError):
        fifo["test"]


def test_in_operator():
    fifo = PacketFifo(10)
    assert 1 not in fifo

    fifo[1] = 0
    assert 1 in fifo


def test_add_multiple():
    fifo = PacketFifo(10)
    fifo[0] = 1
    fifo[1] = 2
    fifo[2] = 3
    assert fifo[0] == 1
    assert fifo[1] == 2
    assert fifo[2] == 3
    assert len(fifo) == 3
    assert fifo


def test_add_overflow_removes_oldest():
    fifo = PacketFifo(2)
    fifo[0] = 1
    fifo[1] = 2

    fifo[2] = 3
    assert len(fifo) == 2
    assert 0 not in fifo
    assert fifo[1] == 2
    assert fifo[2] == 3

    fifo[3] = 4
    assert len(fifo) == 2
    assert 1 not in fifo
    assert fifo[2] == 3
    assert fifo[3] == 4


def test_clear_fifo():
    fifo = PacketFifo(2)
    fifo[0] = 1
    fifo[1] = 2
    fifo.clear()
    assert len(fifo) == 0


def test_del_not_supported():
    fifo = PacketFifo(2)
    fifo[0] = 1

    with pytest.raises(NotImplementedError):
        del fifo[0]


def test_iter_over_indices():
    fifo = PacketFifo(10)
    fifo[1] = 1
    fifo[2] = 2
    fifo[3] = 2

    sum = 0
    for i in fifo:
        sum += i

    assert sum == (1 + 2 + 3)


def test_str():
    fifo = PacketFifo(2)
    assert str(fifo) == "[]"
    fifo[1] = 2
    fifo[2] = 3
    assert str(fifo) == "[1, 2]"


def test_repr():
    fifo = PacketFifo(2)
    assert repr(fifo) == "{}"
    fifo[1] = 2
    fifo[2] = 3
    assert repr(fifo) == "{1: 2, 2: 3}"
