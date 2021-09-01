"""Generic functions for protocol logic."""
import asyncio
import logging
from typing import Awaitable, Callable, Optional, TypeVar

_LOGGER = logging.getLogger(__name__)

HEARTBEAT_INTERVAL = 30
HEARTBEAT_RETRIES = 1  # One regular attempt + retries

MessageType = TypeVar("MessageType")


async def heartbeater(
    name: str,
    sender_func: Callable[[Optional[MessageType]], Awaitable],
    finish_func: Callable[[], None] = lambda: None,
    failure_func: Callable[[Exception], None] = lambda exc: None,
    message_factory: Callable[[], Optional[MessageType]] = lambda: None,
    retries=HEARTBEAT_RETRIES,
    interval=HEARTBEAT_INTERVAL,
):
    """Periodically send heartbeat messages to device."""
    _LOGGER.debug("Starting heartbeat loop (%s)", name)
    count = 0
    attempts = 0
    message = message_factory()
    while True:
        try:
            # Re-attempts are made with no initial delay to more quickly
            # recover a failed heartbeat (if possible)
            if attempts == 0:
                await asyncio.sleep(interval)

            _LOGGER.debug("Sending periodic heartbeat %d (%s)", count, name)
            await sender_func(message)
            _LOGGER.debug("Got heartbeat %d (%s)", count, name)
        except asyncio.CancelledError:
            break
        except Exception as exc:
            attempts += 1
            if attempts > retries:
                _LOGGER.exception(
                    "Heartbeat %d failed after %d tries (%s)", count, attempts, name
                )
                failure_func(exc)
                return
            _LOGGER.debug("Heartbeat %d failed (%s)", count, name)
        else:
            attempts = 0
        finally:
            count += 1

    _LOGGER.debug("Stopping heartbeat loop at %d (%s)", count, name)
    finish_func()
