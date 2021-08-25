"""Unit tests for pyatc.core."""
import pytest

from pyatv.core import StateProducer

# StateProducer


class DummyListener:
    def __init__(self):
        self.foo_called: bool = False
        self.foo_calls: int = 0

    def foo(self) -> None:
        self.foo_called = True
        self.foo_calls += 1

    def bar(self) -> None:
        raise Exception("error")


def test_call_to_unknown_method_does_nothing():
    producer = StateProducer()
    producer.listener.missing()


def test_call_to_existing_method():
    listener = DummyListener()
    producer = StateProducer()
    producer.listener = listener

    producer.listener.foo()
    assert listener.foo_called


def test_call_to_non_live_object():
    def _create():
        # listener will go out of scope when method returns, thus making the weakref in
        # StateProducer lose the reference
        listener = DummyListener()
        producer = StateProducer()
        producer.listener = listener
        return producer

    producer = _create()
    producer.listener.bar()


def test_call_ignore_max_count():
    listener = DummyListener()
    producer = StateProducer(max_calls=2)
    producer.listener = listener

    producer.listener.foo()
    assert listener.foo_calls == 1

    producer.listener.foo()
    assert listener.foo_calls == 2

    producer.listener.foo()
    assert listener.foo_calls == 2
