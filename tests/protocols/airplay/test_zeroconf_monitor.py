"""Unit tests for pyatv.protocols.airplay.zeroconf_monitor."""

import asyncio
from types import SimpleNamespace

import pytest
from zeroconf import ServiceStateChange

from pyatv.helpers import AIRPLAY_SERVICE, get_unique_id
from pyatv.protocols.airplay import zeroconf_monitor
from pyatv.protocols.airplay.zeroconf_monitor import (
    AIRPLAY_SERVICE_TYPE,
    get_watcher,
)

from tests.utils import until

pytestmark = pytest.mark.asyncio

DEVICE_ID = "aa:bb:cc:dd:ee:ff"
OTHER_DEVICE_ID = "11:22:33:44:55:66"
SERVICE_NAME = "Kitchen"


class FakeZeroconf:
    """Fake Zeroconf instance."""


class FakeAsyncZeroconf:
    """Fake AsyncZeroconf keeping track of created instances."""

    instances = []

    def __init__(self):
        self.zeroconf = FakeZeroconf()
        self.close_calls = 0
        FakeAsyncZeroconf.instances.append(self)

    async def async_close(self):
        self.close_calls += 1


class FakeAsyncServiceBrowser:
    """Fake AsyncServiceBrowser keeping track of created instances."""

    instances = []

    def __init__(self, zeroconf, service_type, handlers=None):
        self.zeroconf = zeroconf
        self.service_type = service_type
        self.handlers = handlers or []
        self.cancel_calls = 0
        FakeAsyncServiceBrowser.instances.append(self)

    async def async_cancel(self):
        self.cancel_calls += 1


@pytest.fixture(autouse=True)
def reset_watchers(monkeypatch):
    """Make sure no watchers or fakes leak between tests."""
    monkeypatch.setattr(zeroconf_monitor, "AsyncZeroconf", FakeAsyncZeroconf)
    monkeypatch.setattr(
        zeroconf_monitor, "AsyncServiceBrowser", FakeAsyncServiceBrowser
    )
    FakeAsyncZeroconf.instances = []
    FakeAsyncServiceBrowser.instances = []
    zeroconf_monitor._watchers.clear()
    yield
    zeroconf_monitor._watchers.clear()
    FakeAsyncZeroconf.instances = []
    FakeAsyncServiceBrowser.instances = []


def service_info(device_id=DEVICE_ID):
    """Return a fake AsyncServiceInfo with zeroconf encoded properties."""
    return SimpleNamespace(
        type=AIRPLAY_SERVICE_TYPE,
        name=f"{SERVICE_NAME}.{AIRPLAY_SERVICE_TYPE}",
        properties={
            b"deviceid": device_id.encode(),
            b"flags": b"0x800",
        },
    )


async def test_one_watcher_per_loop():
    loop = asyncio.get_running_loop()

    watcher = get_watcher(loop)

    assert get_watcher(loop) is watcher
    assert len(zeroconf_monitor._watchers) == 1


async def test_subscribe_starts_and_unsubscribe_stops():
    loop = asyncio.get_running_loop()
    watcher = get_watcher(loop)
    received = []

    unsubscribe = await watcher.subscribe(DEVICE_ID, received.append)

    assert watcher.running
    assert watcher.refcount == 1
    assert len(FakeAsyncZeroconf.instances) == 1
    assert len(FakeAsyncServiceBrowser.instances) == 1
    assert FakeAsyncServiceBrowser.instances[0].service_type == AIRPLAY_SERVICE_TYPE

    await unsubscribe()

    assert not watcher.running
    assert watcher.refcount == 0
    assert FakeAsyncServiceBrowser.instances[0].cancel_calls == 1
    assert FakeAsyncZeroconf.instances[0].close_calls == 1
    assert id(loop) not in zeroconf_monitor._watchers


async def test_refcount_multiple_subscribers():
    loop = asyncio.get_running_loop()
    watcher = get_watcher(loop)

    first = await watcher.subscribe(DEVICE_ID, lambda props: None)
    second = await watcher.subscribe(OTHER_DEVICE_ID, lambda props: None)

    assert watcher.refcount == 2
    assert len(FakeAsyncServiceBrowser.instances) == 1

    await first()

    assert watcher.refcount == 1
    assert watcher.running

    await second()

    assert watcher.refcount == 0
    assert not watcher.running


async def test_dispatch_by_identifier():
    loop = asyncio.get_running_loop()
    watcher = get_watcher(loop)
    received = []

    unsubscribe = await watcher.subscribe(DEVICE_ID, received.append)
    watcher._dispatch(service_info())

    assert received == [{"deviceid": DEVICE_ID, "flags": "0x800"}]

    await unsubscribe()


async def test_dispatch_unknown_identifier_ignored():
    loop = asyncio.get_running_loop()
    watcher = get_watcher(loop)
    received = []

    unsubscribe = await watcher.subscribe(OTHER_DEVICE_ID, received.append)
    watcher._dispatch(service_info())

    assert received == []

    await unsubscribe()


async def test_dispatch_uses_same_identifier_as_scan():
    loop = asyncio.get_running_loop()
    watcher = get_watcher(loop)
    info = service_info()
    received = []

    properties = {
        key.decode(): value.decode() for key, value in info.properties.items()
    }
    scan_identifier = get_unique_id(AIRPLAY_SERVICE, info.name, properties)

    assert scan_identifier == DEVICE_ID

    unsubscribe = await watcher.subscribe(scan_identifier, received.append)
    watcher._dispatch(info)

    assert received == [properties]

    await unsubscribe()


async def test_unsubscribe_is_idempotent():
    loop = asyncio.get_running_loop()
    watcher = get_watcher(loop)

    unsubscribe = await watcher.subscribe(DEVICE_ID, lambda props: None)

    await unsubscribe()
    await unsubscribe()

    assert watcher.refcount == 0
    assert not watcher.running
    assert FakeAsyncServiceBrowser.instances[0].cancel_calls == 1
    assert FakeAsyncZeroconf.instances[0].close_calls == 1


async def test_double_subscribe_same_callback():
    loop = asyncio.get_running_loop()
    watcher = get_watcher(loop)
    received = []

    first = await watcher.subscribe(DEVICE_ID, received.append)
    second = await watcher.subscribe(DEVICE_ID, received.append)

    assert watcher.refcount == 1
    assert len(FakeAsyncServiceBrowser.instances) == 1

    watcher._dispatch(service_info())

    assert received == [{"deviceid": DEVICE_ID, "flags": "0x800"}]

    await second()

    assert watcher.refcount == 0
    assert not watcher.running

    # First subscription was already removed by the second unsubscribe
    await first()

    assert watcher.refcount == 0
    assert not watcher.running
    assert FakeAsyncZeroconf.instances[0].close_calls == 1


async def test_new_watcher_created_after_last_unsubscribe():
    loop = asyncio.get_running_loop()
    first_watcher = get_watcher(loop)

    unsubscribe = await first_watcher.subscribe(DEVICE_ID, lambda props: None)
    await unsubscribe()

    assert id(loop) not in zeroconf_monitor._watchers

    second_watcher = get_watcher(loop)

    assert second_watcher is not first_watcher


async def test_pending_resolve_task_is_cancelled_on_stop(monkeypatch):
    class BlockingServiceInfo:
        def __init__(self, service_type, name):
            self.type = service_type
            self.name = name
            self.properties = {b"deviceid": DEVICE_ID.encode()}

        def load_from_cache(self, zeroconf):
            return False

        async def async_request(self, zeroconf, timeout):
            await asyncio.Event().wait()

    monkeypatch.setattr(zeroconf_monitor, "AsyncServiceInfo", BlockingServiceInfo)

    loop = asyncio.get_running_loop()
    watcher = get_watcher(loop)
    unsubscribe = await watcher.subscribe(DEVICE_ID, lambda props: None)

    watcher._on_change(
        FakeZeroconf(),
        AIRPLAY_SERVICE_TYPE,
        service_info().name,
        ServiceStateChange.Added,
    )

    await until(lambda: len(watcher._pending_tasks) == 1)
    task = next(iter(watcher._pending_tasks))

    await unsubscribe()

    assert task.cancelled()
    assert not watcher._pending_tasks
    assert not watcher.running


async def test_on_change_ignored_without_subscribers():
    loop = asyncio.get_running_loop()
    watcher = get_watcher(loop)

    watcher._on_change(
        FakeZeroconf(),
        AIRPLAY_SERVICE_TYPE,
        service_info().name,
        ServiceStateChange.Added,
    )

    assert not watcher._pending_tasks
