"""Core module of pyatv."""
from abc import abstractmethod
import asyncio
from enum import Enum
import logging
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

from pyatv.const import FeatureName, PairingRequirement, PairingState, Protocol
from pyatv.core.protocol import MessageDispatcher
from pyatv.exceptions import (
    InvalidStateError,
    NotSupportedError,
    PairingError,
    PairingFailureReason,
)
from pyatv.interface import (
    BaseConfig,
    BaseService,
    PairingHandler,
    Playing,
    PushUpdater,
)
from pyatv.support import error_handler
from pyatv.support.http import ClientSessionManager
from pyatv.support.state_producer import StateProducer

_LOGGER = logging.getLogger(__name__)

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


class AbstractPairingHandler(PairingHandler):
    """Abstract pairing handler class.

    This class add an internal state to ensure methods are called in the correct order.
    """

    def __init__(
        self,
        session_manager: ClientSessionManager,
        service: BaseService,
        device_provides_pin: bool,
    ) -> None:
        """Initialize a new instance of AbstractPairingHandler."""
        super().__init__(session_manager, service)
        self.session_manager = session_manager
        self._device_provides_pin = device_provides_pin
        self._pin: Optional[str] = None
        self._state: PairingState = PairingState.NotStarted
        self._reason: PairingFailureReason = PairingFailureReason.Unspecified

    @property
    def state(self) -> PairingState:
        """Return current state of pairing process."""
        return self._state

    @property
    def failure_reason(self) -> PairingFailureReason:
        """If pairing has failed, return the reason for doing so.

        The value of this property is only valid if `state` is `PairingState.Failed`.
        """
        return self._reason

    @property
    def device_provides_pin(self) -> bool:
        """Return True if remote device presents PIN code, else False."""
        return self._device_provides_pin

    @property
    def has_paired(self) -> bool:
        """If a successful pairing has been performed."""
        return self._state == PairingState.Finished

    def pin(self, pin: Union[str, int]) -> None:
        """Pin code used for pairing."""
        self._pin = str(pin).zfill(4)
        _LOGGER.debug(
            "Changing PIN for %s to %s", self.service.protocol.name, self._pin
        )

    async def begin(self) -> None:
        """Start pairing process."""
        _LOGGER.debug("Start pairing %s", self.service.protocol.name)

        if self.state != PairingState.NotStarted:
            raise InvalidStateError("pairing process has already started")

        # If a PIN is supposed to be entered on the device, that PIN must be set here
        if not self.device_provides_pin and self._pin is None:
            self._state = PairingState.Failed
            raise InvalidStateError("no pin code set")

        self._state = PairingState.Started
        try:
            await error_handler(self._pair_begin, PairingError)
        except Exception:
            self._state = PairingState.Failed
            raise

    async def finish(self) -> None:
        """Stop pairing process."""
        _LOGGER.debug("Finish pairing %s", self.service.protocol.name)

        if self.state == PairingState.Failed:
            raise PairingError(
                f"pairing failed with reason: {self.failure_reason.name}",
                self.failure_reason,
            )
        if self.state != PairingState.Started:
            raise InvalidStateError("pairing process has not started")
        if self.device_provides_pin and self._pin is None:
            self._state = PairingState.Failed
            raise InvalidStateError("no pin code")

        try:
            self.service.credentials = await error_handler(
                self._pair_finish, PairingError
            )
        except Exception as ex:
            self._state = PairingState.Failed
            if isinstance(ex, PairingError):
                self._reason = ex.failure_reason
            raise
        else:
            self._state = PairingState.Finished

    @abstractmethod
    async def _pair_begin(self) -> None:
        """Start pairing process.

        This must be implemented by the protocol.
        """
        raise NotSupportedError()

    @abstractmethod
    async def _pair_finish(self) -> str:
        """Stop pairing process.

        This must be implemented by the protocol.
        """
        raise NotSupportedError()

    def _set_failure(self, reason: PairingFailureReason) -> None:
        """Change pairing state to Failed with provided reason.

        Only to be called from subclasses.
        """
        self._state = PairingState.Failed
        self._reason = reason


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
