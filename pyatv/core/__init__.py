"""Core module of pyatv."""
import asyncio
from enum import Enum
from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    List,
    Mapping,
    NamedTuple,
    Optional,
    Set,
    Union,
)

from pyatv.const import FeatureName, PairingRequirement, Protocol
from pyatv.core.protocol import MessageDispatcher
from pyatv.interface import BaseConfig, BaseService, Playing, PushUpdater
from pyatv.support.http import ClientSessionManager
from pyatv.support.state_producer import StateProducer

TakeoverMethod = Callable[
    ...,
    Callable[[], None],
]


# pylint: disable=invalid-name


class UpdatedState(Enum):
    """Name of states that can be updated."""

    Playing = 1
    """Playing state in metadata was updated."""

    Volume = 2
    """Volume was updated."""


# pylint: enable=invalid-name


class StateMessage(NamedTuple):
    """Message sent when state of something changed."""

    protocol: Protocol
    state: UpdatedState

    # Type depending on value of state:
    # - UpdatedState.Playing -> interface.Playing
    # - UpdatedState.Volume -> float
    value: Any

    def __str__(self):
        """Return string representation of object."""
        return f"[{self.protocol.name}.{self.state.name} -> {self.value}]"


def _no_filter(message: StateMessage) -> bool:
    return True


CoreStateDispatcher = MessageDispatcher[UpdatedState, StateMessage]


class ProtocolStateDispatcher:
    """Dispatch internal protocol state updates to listeners."""

    def __init__(
        self,
        protocol: Protocol,
        core_dispatcher: CoreStateDispatcher,
    ) -> None:
        """Initialize a new ProtocolStateDispatcher instance."""
        self._protocol = protocol
        self._core_dispatcher = core_dispatcher

    def create_copy(self, protocol: Protocol) -> "ProtocolStateDispatcher":
        """Create a copy of this instance but with a new protocol."""
        return ProtocolStateDispatcher(protocol, self._core_dispatcher)

    def listen_to(
        self,
        state: UpdatedState,
        func: Callable[[StateMessage], Union[None, Awaitable[None]]],
        message_filter: Callable[[StateMessage], bool] = _no_filter,
    ) -> None:
        """Listen to a specific type of message type."""
        return self._core_dispatcher.listen_to(state, func, message_filter)

    def dispatch(self, state: UpdatedState, value: Any) -> List[asyncio.Task]:
        """Dispatch a message to listeners."""
        return self._core_dispatcher.dispatch(
            state, StateMessage(self._protocol, state, value)
        )


class MutableService(BaseService):
    """Mutable version of BaseService allowing some fields to be changed.

    This is an internal implementation of BaseService that allows protocols to change
    some fields during set up. The mutable property is not exposed outside of core.
    """

    def __init__(
        self,
        identifier: Optional[str],
        protocol: Protocol,
        port: int,
        properties: Optional[Mapping[str, str]],
        credentials: Optional[str] = None,
        password: Optional[str] = None,
        enabled: bool = True,
    ) -> None:
        """Initialize a new MutableService."""
        super().__init__(
            identifier, protocol, port, properties, credentials, password, enabled
        )
        self._requires_password = False
        self._pairing_requirement = PairingRequirement.Unsupported

    @property
    def requires_password(self) -> bool:
        """Return if a password is required to access service."""
        return self._requires_password

    @requires_password.setter
    def requires_password(self, value: bool) -> None:
        """Change if password is required or not."""
        self._requires_password = value

    @property
    def pairing(self) -> PairingRequirement:
        """Return if pairing is required by service."""
        return self._pairing_requirement

    @pairing.setter
    def pairing(self, value: PairingRequirement) -> None:
        """Change if pairing is required by service."""
        self._pairing_requirement = value

    def __deepcopy__(self, memo) -> "BaseService":
        """Return deep-copy of instance."""
        copy = MutableService(
            self.identifier,
            self.protocol,
            self.port,
            self.properties,
            self.credentials,
            self.password,
            self.enabled,
        )
        copy.pairing = self.pairing
        copy.requires_password = self.requires_password
        return copy


class AbstractPushUpdater(PushUpdater):
    """Abstract push updater class.

    This class adds a `post_update` method that will publishes a new state, but only
    if it has been updated.
    """

    def __init__(self, state_dispatcher: ProtocolStateDispatcher):
        """Initialize a new AbstractPushUpdater."""
        super().__init__()
        self.loop: asyncio.AbstractEventLoop = asyncio.get_event_loop()
        self.state_dispatcher = state_dispatcher
        self._previous_state: Optional[Playing] = None

    def post_update(self, playing: Playing) -> None:
        """Post an update to listener."""
        if playing != self._previous_state:
            # Dispatch message using message dispatcher
            self.state_dispatcher.dispatch(UpdatedState.Playing, playing)

            # Publish using regular (external) interface. This shall be removed at
            # some point in time.
            self.loop.call_soon(self.listener.playstatus_update, self, playing)

        self._previous_state = playing


class SetupData(NamedTuple):
    """Information for setting up a protocol."""

    protocol: Protocol
    connect: Callable[[], Awaitable[bool]]
    close: Callable[[], Set[asyncio.Task]]
    device_info: Callable[[], Dict[str, Any]]
    interfaces: Mapping[Any, Any]
    features: Set[FeatureName]


class Core:
    """Instance for protocols to access core features."""

    def __init__(
        self,
        loop: asyncio.AbstractEventLoop,
        config: BaseConfig,
        service: BaseService,
        device_listener: StateProducer,
        session_manager: ClientSessionManager,
        takeover: TakeoverMethod,
        state_dispatcher: ProtocolStateDispatcher,
    ) -> None:
        """Initialize a new Core instance."""
        self.loop = loop
        self.config = config
        self.service = service
        self.device_listener = device_listener
        self.session_manager = session_manager
        self.takeover = takeover
        self.state_dispatcher = state_dispatcher
