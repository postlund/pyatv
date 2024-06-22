"""Generic functions for protocol logic."""

import asyncio
import inspect
import logging
from typing import (
    Awaitable,
    Callable,
    Dict,
    Generic,
    List,
    Optional,
    Tuple,
    TypeVar,
    Union,
)

_LOGGER = logging.getLogger(__name__)

HEARTBEAT_INTERVAL = 30
HEARTBEAT_RETRIES = 1  # One regular attempt + retries

MessageType = TypeVar("MessageType")  # pylint: disable=invalid-name

DispatchType = TypeVar("DispatchType")  # pylint: disable=invalid-name
DispatchMessage = TypeVar("DispatchMessage")
DispatchFunc = Callable[[DispatchMessage], Union[None, Awaitable[None]]]
DispatchFilterFunc = Callable[[DispatchMessage], bool]


def _no_filter(message: MessageType) -> bool:
    return True


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
                _LOGGER.debug(
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


class MessageDispatcher(Generic[DispatchType, DispatchMessage]):
    """Dispatch message to listeners based on a type."""

    def __init__(self) -> None:
        """Initialize a new MessageDispatcher instance."""
        self.__listeners: Dict[
            DispatchType, List[Tuple[DispatchFilterFunc, DispatchFunc]]
        ] = {}

    def listen_to(
        self,
        dispatch_type: DispatchType,
        func: DispatchFunc,
        message_filter: DispatchFilterFunc = _no_filter,
    ) -> None:
        """Listen to a specific type of message type."""
        self.__listeners.setdefault(dispatch_type, []).append((message_filter, func))

    def dispatch(
        self, dispatch_type: DispatchType, message: DispatchMessage
    ) -> List[asyncio.Task]:
        """Dispatch a message to listeners."""

        async def _call_listener(func):
            # Make sure to catch any exceptions caused by the listener so we don't get
            # unfished tasks laying around
            try:
                await func
            except asyncio.CancelledError:
                pass
            except Exception:
                _LOGGER.exception("error during dispatch")

        tasks = []
        loop = asyncio.get_event_loop()
        listeners = self.__listeners.get(dispatch_type, [])
        for func in [func for filter_func, func in listeners if filter_func(message)]:
            _LOGGER.debug(
                "Dispatching message with type %s to %s",
                dispatch_type,
                func,
            )
            if inspect.iscoroutinefunction(func):
                tasks.append(asyncio.ensure_future(_call_listener(func(message))))
            else:
                loop.call_soon(func, message)
        return tasks
