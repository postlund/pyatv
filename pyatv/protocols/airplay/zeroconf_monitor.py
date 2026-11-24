"""Shared, loop-scoped watcher for AirPlay TXT record ("flags") changes.

Multiple concurrently connected AirPlay devices all want the same
_airplay._tcp.local. mDNS traffic. Rather than each device connection opening
its own zeroconf socket, one AsyncServiceBrowser is shared per event loop and
reference counted; updates are dispatched to subscribers by device identifier.
"""

import asyncio
import logging
from typing import Any, Callable, Coroutine, Dict, Mapping, Optional, Set, Union

from zeroconf import ServiceStateChange, Zeroconf
from zeroconf.asyncio import AsyncServiceBrowser, AsyncServiceInfo, AsyncZeroconf

from pyatv.helpers import AIRPLAY_SERVICE, get_unique_id

_LOGGER = logging.getLogger(__name__)

AIRPLAY_SERVICE_TYPE = f"{AIRPLAY_SERVICE}."

PropertiesCallback = Callable[[Mapping[str, str]], None]
Unsubscribe = Callable[[], Coroutine[Any, Any, None]]


def _decode_property(value: Union[bytes, str]) -> str:
    """Decode a zeroconf TXT record key or value into a string."""
    return value.decode() if isinstance(value, bytes) else value


class _SharedAirPlayWatcher:
    """Owns exactly one AsyncZeroconf + AsyncServiceBrowser for one event loop."""

    def __init__(self, loop: asyncio.AbstractEventLoop) -> None:
        """Initialize a new _SharedAirPlayWatcher instance."""
        self._loop = loop
        self._aiozc: Optional[AsyncZeroconf] = None
        self._browser: Optional[AsyncServiceBrowser] = None
        self._subscribers: Dict[str, Set[PropertiesCallback]] = {}
        self._pending_tasks: Set[asyncio.Task] = set()

    @property
    def refcount(self) -> int:
        """Return number of registered subscriber callbacks."""
        return sum(len(callbacks) for callbacks in self._subscribers.values())

    @property
    def running(self) -> bool:
        """Return if the shared zeroconf browser is running."""
        return self._browser is not None

    async def subscribe(
        self, identifier: str, callback: PropertiesCallback
    ) -> Unsubscribe:
        """Register callback for one device's mDNS TXT record updates.

        Subscribing the same callback for the same identifier more than once has
        no additional effect. The returned unsubscribe function is idempotent.
        """
        callbacks = self._subscribers.setdefault(identifier, set())
        already_subscribed = callback in callbacks
        callbacks.add(callback)

        if not already_subscribed and not self.running:
            try:
                await self._start()
            except Exception:
                callbacks.discard(callback)
                if not callbacks:
                    del self._subscribers[identifier]
                raise

        async def _unsubscribe() -> None:
            await self._unsubscribe(identifier, callback)

        return _unsubscribe

    async def _unsubscribe(self, identifier: str, callback: PropertiesCallback) -> None:
        callbacks = self._subscribers.get(identifier)

        # Guard against calling the same unsubscribe function more than once, as
        # well as double subscriptions of the same callback.
        if callbacks is None or callback not in callbacks:
            return

        callbacks.discard(callback)
        if not callbacks:
            del self._subscribers[identifier]

        if not self._subscribers:
            await self._stop()

    async def _start(self) -> None:
        _LOGGER.debug("Starting shared AirPlay zeroconf watcher")
        aiozc = AsyncZeroconf()
        try:
            browser = AsyncServiceBrowser(
                aiozc.zeroconf, AIRPLAY_SERVICE_TYPE, handlers=[self._on_change]
            )
        except Exception:
            await aiozc.async_close()
            raise

        self._aiozc = aiozc
        self._browser = browser

    async def _stop(self) -> None:
        _LOGGER.debug("Stopping shared AirPlay zeroconf watcher (no subscribers left)")
        await self._cancel_pending_tasks()

        if self._browser is not None:
            browser, self._browser = self._browser, None
            await browser.async_cancel()

        if self._aiozc is not None:
            aiozc, self._aiozc = self._aiozc, None
            await aiozc.async_close()

        self._unregister()

    def _unregister(self) -> None:
        key = id(self._loop)
        if _watchers.get(key) is self:
            del _watchers[key]

    async def _cancel_pending_tasks(self) -> None:
        tasks = list(self._pending_tasks)
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self._pending_tasks.clear()

    def _on_change(
        self,
        zeroconf: Zeroconf,
        service_type: str,
        name: str,
        state_change: ServiceStateChange,
    ) -> None:
        """Handle a service state change reported by the zeroconf browser."""
        if not self._subscribers:
            return

        _LOGGER.debug(
            "AirPlay zeroconf watcher changed: name: %s, service_type: %s, "
            "state_change: %s",
            name,
            service_type,
            state_change,
        )

        # Always continue on the loop owning this watcher, as the callback might
        # be called from a zeroconf thread.
        self._loop.call_soon_threadsafe(
            self._handle_change, zeroconf, service_type, name
        )

    def _handle_change(self, zeroconf: Zeroconf, service_type: str, name: str) -> None:
        if not self._subscribers:
            return

        info = AsyncServiceInfo(service_type, name)
        if info.load_from_cache(zeroconf):
            self._dispatch(info)
        else:
            task = self._loop.create_task(self._resolve_and_dispatch(zeroconf, info))
            self._pending_tasks.add(task)
            task.add_done_callback(self._pending_tasks.discard)

    async def _resolve_and_dispatch(
        self, zeroconf: Zeroconf, info: AsyncServiceInfo
    ) -> None:
        try:
            if await info.async_request(zeroconf, 3000):
                self._dispatch(info)
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Failed to resolve AirPlay zeroconf service")

    def _dispatch(self, info: AsyncServiceInfo) -> None:
        properties: Dict[str, str] = {
            _decode_property(key): _decode_property(value)
            for key, value in info.properties.items()
        }

        # Zeroconf includes a trailing dot in the service type, whereas the
        # identifiers derived during scanning do not.
        identifier = get_unique_id(info.type.rstrip("."), info.name, properties)
        if identifier is None or identifier not in self._subscribers:
            return

        for callback in list(self._subscribers[identifier]):
            callback(properties)


_watchers: Dict[int, _SharedAirPlayWatcher] = {}


def get_watcher(loop: asyncio.AbstractEventLoop) -> _SharedAirPlayWatcher:
    """Return the shared AirPlay zeroconf watcher for a given event loop."""
    key = id(loop)
    watcher = _watchers.get(key)
    if watcher is None:
        watcher = _SharedAirPlayWatcher(loop)
        _watchers[key] = watcher
    return watcher
