"""Unit tests for pyatv.core.protocol."""
import asyncio
import math
from typing import Any, Optional

import pytest

from pyatv.core.protocol import heartbeater

from tests.utils import total_sleep_time, until

pytestmark = pytest.mark.asyncio


class HeartbeatMonitor:
    def __init__(self) -> None:
        self.task: Optional[asyncio.Task] = None
        self.send_call_count: int = 0
        self.send_event: asyncio.Event = asyncio.Event()
        self.send_message: Optional[Any] = None
        self.finish_called: bool = False
        self.failure_called: bool = False
        self.make_send_fail: bool = False

    def start(self, message_factory=None, retries=0, interval=5):
        self.task = asyncio.ensure_future(
            heartbeater(
                "name",
                self.send,
                self.finish,
                self.failure,
                message_factory=message_factory or (lambda: None),
                retries=retries,
                interval=interval,
            )
        )

    async def stop(self) -> None:
        self.task.cancel()
        await self.task

    def next_lap(self) -> None:
        self.send_event.set()

    async def send(self, message) -> None:
        self.send_call_count += 1
        self.send_message = message

        if self.make_send_fail:
            raise Exception("send failed")
        else:
            await self.send_event.wait()
            self.send_event.clear()

    def finish(self) -> None:
        self.finish_called = True

    def failure(self, exc: Exception) -> None:
        self.failure_called = True


@pytest.fixture(name="monitor")
async def monitor_fixture():
    monitor = HeartbeatMonitor()
    yield monitor
    await monitor.stop()


async def test_send_heartbeats(monitor):
    monitor.start()

    for lap in range(1, 4):
        await until(lambda: monitor.send_call_count == lap)
        monitor.next_lap()


async def test_failure_called_on_send_error(monitor):
    monitor.make_send_fail = True
    monitor.start()

    await until(lambda: monitor.failure_called)
    assert monitor.send_call_count == 1


async def test_finish_called_on_cancel(monitor):
    monitor.start()

    await until(lambda: monitor.send_call_count == 1)
    await monitor.stop()

    await until(lambda: monitor.finish_called)
    assert not monitor.failure_called


async def test_retry_before_failure(monitor):
    monitor.make_send_fail = True
    monitor.start(retries=3, interval=5)

    await until(lambda: monitor.send_call_count == 4)
    assert monitor.failure_called
    assert not monitor.finish_called


async def test_sleep_between_send(monitor):
    monitor.start(interval=5)

    await until(lambda: monitor.send_call_count == 1)
    assert math.isclose(total_sleep_time(), 5)
    monitor.next_lap()

    await until(lambda: monitor.send_call_count == 2)
    assert math.isclose(total_sleep_time(), 10)


async def test_no_sleep_for_first_retry(monitor):
    monitor.make_send_fail = True
    monitor.start(retries=1, interval=5)

    await until(lambda: monitor.send_call_count == 2)
    monitor.next_lap()
    await until(lambda: monitor.failure_called)
    assert math.isclose(total_sleep_time(), 5)


async def test_message_is_passed_to_send(monitor):
    message = object()
    monitor.start(message_factory=lambda: message)

    await until(lambda: monitor.send_call_count == 1)
    assert monitor.send_message is message
