"""Shared, loop-scoped watcher for AirPlay TXT record ('flags') changes.

Multiple concurrently connected AirPlay devices all want the same
_airplay._tcp.local. mDNS traffic. Rather than each device connection opening
its own zeroconf socket, one AsyncServiceBrowser is shared per event loop and
reference counted; updates are dispatched to subscribers by device identifier.
"""
import asyncio
import logging
from typing import Awaitable, Callable, Dict, Mapping, Optional, Set

from zeroconf import ServiceStateChange, Zeroconf
from zeroconf.asyncio import AsyncServiceBrowser, AsyncServiceInfo, AsyncZeroconf

from pyatv.helpers import get_unique_id

_LOGGER = logging.getLogger(__name__)

AIRPLAY_SERVICE_TYPE = "_airplay._tcp.local."

PropertiesCallback = Callable[[Mapping[str, str]], None]
Unsubscribe = Callable[[], Awaitable[None]]


class _SharedAirPlayWatcher:
    """Owns exactly one AsyncZeroconf + AsyncServiceBrowser for one event loop."""

    def __init__(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop
        self._aiozc: Optional[AsyncZeroconf] = None
        self._browser: Optional[AsyncServiceBrowser] = None
        self._subscribers: Dict[str, Set[PropertiesCallback]] = {}
        self._refcount = 0

    async def subscribe(
        self, identifier: str, callback: PropertiesCallback
    ) -> Unsubscribe:
        """Register callback for one device's mDNS TXT record updates."""
        self._refcount += 1
        if self._refcount == 1:
            await self._start()

        self._subscribers.setdefault(identifier, set()).add(callback)

        async def _unsubscribe() -> None:
            callbacks = self._subscribers.get(identifier)
            if callbacks:
                callbacks.discard(callback)
                if not callbacks:
                    del self._subscribers[identifier]
            self._refcount -= 1
            if self._refcount == 0:
                await self._stop()

        return _unsubscribe

    async def _start(self) -> None:
        _LOGGER.debug("Starting shared AirPlay zeroconf watcher")
        self._aiozc = AsyncZeroconf()
        self._browser = AsyncServiceBrowser(
            self._aiozc.zeroconf, AIRPLAY_SERVICE_TYPE, handlers=[self._on_change]
        )

    async def _stop(self) -> None:
        _LOGGER.debug("Stopping shared AirPlay zeroconf watcher (no subscribers left)")
        if self._browser:
            await self._browser.async_cancel()
            self._browser = None
        if self._aiozc:
            await self._aiozc.async_close()
            self._aiozc = None

    def _on_change(
        self,
        zeroconf: Zeroconf,
        service_type: str,
        name: str,
        state_change: ServiceStateChange,
    ) -> None:
        _LOGGER.debug("AirPlay zeroconf watcher changed: name: %s, service_type: %s, state_change: %s", name, service_type, state_change )
        info = AsyncServiceInfo(service_type, name)
        if info.load_from_cache(zeroconf):
            self._dispatch(info)
        else:
            asyncio.ensure_future(self._resolve_and_dispatch(zeroconf, info))

    async def _resolve_and_dispatch(
        self, zeroconf: Zeroconf, info: AsyncServiceInfo
    ) -> None:
        if await info.async_request(zeroconf, 3000):
            self._dispatch(info)

    def _dispatch(self, info: AsyncServiceInfo) -> None:
        properties = {
            k.decode() if isinstance(k, bytes) else k: (
                v.decode() if isinstance(v, bytes) else v
            )
            for k, v in info.properties.items()
        }
        identifier = get_unique_id(info.type, info.name, properties)
        if identifier is None or identifier not in self._subscribers:
            return
        for callback in list(self._subscribers[identifier]):
            callback(properties)


_watchers: Dict[int, _SharedAirPlayWatcher] = {}


def get_watcher(loop: asyncio.AbstractEventLoop) -> _SharedAirPlayWatcher:
    """Return the shared AirPlay zeroconf watcher for a given event loop."""
    key = id(loop)
    if key not in _watchers:
        _watchers[key] = _SharedAirPlayWatcher(loop)
    return _watchers[key]
