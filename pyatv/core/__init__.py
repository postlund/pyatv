"""Core module of pyatv."""
from typing import Generic, Optional, TypeVar, cast
import weakref

NO_MAX_CALLS = 0

StateListener = TypeVar("StateListener")


class _ListenerProxy:
    """Proxy to call functions in a listener.

    A proxy instance maintains a weak reference to a listener object and allows calling
    functions in the listener. If no listener is set or the weak reference has expired,
    a null-function (doing nothing) is returned so that nothing happens. This makes it
    safe to call functions without having to check if either a listener has been set at
    all or if the listener implements the called function.
    """

    def __init__(self, producer, listener: StateListener):
        """Initialize a new ListenerProxy instance."""
        self.__producer = producer
        self.__listener: StateListener = listener

    def __getattr__(self, attr):
        """Dynamically find target method in listener."""
        producer = self.__producer()

        if producer:
            # Count number of calls to _any_ method and if total count exceeds the
            # given max limit, then bail out
            producer.calls_made += 1
            if producer.max_calls and producer.calls_made > producer.max_calls:
                return lambda *args, **kwargs: None

        if self.__listener is not None:
            listener = self.__listener()
            if hasattr(listener, attr):
                return getattr(listener, attr)

        return lambda *args, **kwargs: None


class StateProducer(Generic[StateListener]):
    """Base class for objects announcing state changes to a listener."""

    def __init__(self, max_calls: int = NO_MAX_CALLS) -> None:
        """Initialize a new StateProducer instance."""
        self.__listener: Optional[weakref.ReferenceType[StateListener]] = None
        self.max_calls = max_calls
        self.calls_made = 0

    @property
    def listener(self) -> StateListener:
        """Return current listener object."""
        return cast(StateListener, _ListenerProxy(weakref.ref(self), self.__listener))

    @listener.setter
    def listener(self, target: StateListener) -> None:
        """Change current listener object.

        Set to None to remove active listener.
        """
        self.__listener = weakref.ref(target) if target is not None else None
