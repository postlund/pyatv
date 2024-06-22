"""Unit tests for pyatc.core."""

import pytest

from pyatv.support.state_producer import StateProducer

# StateProducer


class DummyStateProducer(StateProducer):
    def __init__(self):
        super().__init__()
        self.state_was_updated_called = False

    def state_was_updated(self) -> None:
        self.state_was_updated_called = True


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


def test_call_state_was_updated_after_update_no_listener():
    producer = DummyStateProducer()

    producer.listener.missing()
    assert producer.state_was_updated_called

    producer.state_was_updated_called = False
    producer.listener.foo()
    assert producer.state_was_updated_called


def test_call_state_was_updated_after_update_with_listener():
    listener = DummyListener()
    producer = DummyStateProducer()
    producer.listener = listener

    producer.listener.missing()
    assert not producer.state_was_updated_called

    producer.listener.foo()
    assert producer.state_was_updated_called
