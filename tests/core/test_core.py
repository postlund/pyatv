"""Unit tests for pyatv.core."""
from unittest.mock import ANY, MagicMock

import pytest

from pyatv import exceptions
from pyatv.conf import ManualService
from pyatv.const import PairingState, Protocol
from pyatv.core import (
    AbstractPairingHandler,
    AbstractPushUpdater,
    CoreStateDispatcher,
    ProtocolStateDispatcher,
    StateMessage,
    UpdatedState,
)
from pyatv.interface import Playing

# PUSH UPDATER


class PushUpdaterDummy(AbstractPushUpdater):
    def active(self) -> bool:
        """Return if push updater has been started."""
        raise exceptions.NotSupportedError()

    def start(self, initial_delay: int = 0) -> None:
        """Begin to listen to updates.

        If an error occurs, start must be called again.
        """
        raise exceptions.NotSupportedError()

    def stop(self) -> None:
        """No longer forward updates to listener."""
        raise exceptions.NotSupportedError()


@pytest.mark.parametrize("updates", [1, 2, 3])
def test_post_ignore_duplicate_update(event_loop, mrp_state_dispatcher, updates):
    listener = MagicMock()
    playing = Playing()

    def _state_changed(message):
        assert message.protocol == Protocol.MRP
        assert message.state == UpdatedState.Playing
        listener.state_updated(message.value)

    async def _post_updates(repeats: int):
        updater = PushUpdaterDummy(mrp_state_dispatcher)
        updater.listener = listener
        mrp_state_dispatcher.listen_to(UpdatedState.Playing, _state_changed)
        for _ in range(repeats):
            updater.post_update(playing)

    event_loop.run_until_complete(_post_updates(updates))

    assert listener.playstatus_update.call_count == 1
    listener.playstatus_update.assert_called_once_with(ANY, playing)
    listener.state_updated.assert_called_once_with(playing)


# PAIRING HANDLER


class DummyPairingHandler(AbstractPairingHandler):
    def __init__(self, session_manager, service, device_provides_pin):
        super().__init__(session_manager, service, device_provides_pin)
        self.begin_call_count = 0
        self.finish_call_count = 0
        self.begin_error = None
        self.finish_error = None

    @property
    def begin_called(self):
        return self.begin_call_count > 0

    @property
    def finish_called(self):
        return self.finish_call_count > 0

    async def _pair_begin(self):
        self.begin_call_count += 1
        if self.begin_error is not None:
            raise self.begin_error

    async def _pair_finish(self):
        self.finish_call_count += 1
        if self.finish_error is not None:
            raise self.finish_error
        return self._pin  # PIN code is returned as credentials


@pytest.fixture(name="pairing_service")
def pairing_service_fixture():
    yield ManualService("id", Protocol.MRP, 1234, {})


@pytest.fixture(name="pairing_handler")
def pairing_handler_fixture(session_manager, pairing_service, device_provides_pin):
    yield DummyPairingHandler(session_manager, pairing_service, device_provides_pin)


@pytest.mark.parametrize("device_provides_pin", [True])
async def test_pairing_begin_starts_pairing_process(pairing_handler):
    assert pairing_handler.state == PairingState.NotStarted

    await pairing_handler.begin()

    assert pairing_handler.begin_called
    assert pairing_handler.state == PairingState.Started


@pytest.mark.parametrize("device_provides_pin", [True])
async def test_pairing_begin_can_only_be_called_once(pairing_handler):
    await pairing_handler.begin()

    with pytest.raises(exceptions.InvalidStateError):
        await pairing_handler.begin()

    assert pairing_handler.begin_call_count == 1

    # Calling begin more than once does not invalidate the state (it is ignored)
    assert pairing_handler.state == PairingState.Started


@pytest.mark.parametrize("device_provides_pin", [True])
async def test_pairing_begin_sets_error_state_on_exception(pairing_handler):
    pairing_handler.begin_error = Exception("fail")

    with pytest.raises(exceptions.PairingError):
        await pairing_handler.begin()

    assert pairing_handler.state == PairingState.Failed


@pytest.mark.parametrize("device_provides_pin", [True])
async def test_pairing_finish_if_not_started(pairing_handler):
    assert pairing_handler.state == PairingState.NotStarted

    with pytest.raises(exceptions.InvalidStateError):
        await pairing_handler.finish()

    assert pairing_handler.state == PairingState.NotStarted


@pytest.mark.parametrize("device_provides_pin", [True])
async def test_pairing_finish_raises_on_missing_pin(pairing_handler):
    await pairing_handler.begin()
    with pytest.raises(exceptions.InvalidStateError):
        await pairing_handler.finish()

    # Calling without PIN makes process fail
    assert pairing_handler.state == PairingState.Failed


@pytest.mark.parametrize("device_provides_pin", [True])
async def test_pairing_finish_with_success(pairing_handler, pairing_service):
    assert pairing_service.credentials is None
    assert not pairing_handler.has_paired

    await pairing_handler.begin()
    pairing_handler.pin("1234")
    await pairing_handler.finish()

    assert pairing_handler.state == PairingState.Finished
    assert pairing_handler.begin_called
    assert pairing_handler.finish_called
    assert pairing_handler.has_paired
    assert pairing_service.credentials == "1234"


@pytest.mark.parametrize("device_provides_pin", [True])
async def test_pairing_finish_can_only_be_called_once(pairing_handler):
    await pairing_handler.begin()
    pairing_handler.pin("1234")
    await pairing_handler.finish()

    with pytest.raises(exceptions.InvalidStateError):
        await pairing_handler.finish()

    assert pairing_handler.finish_call_count == 1

    # Calling begin more than once does not invalidate the state (it is ignored)
    assert pairing_handler.state == PairingState.Finished


@pytest.mark.parametrize("device_provides_pin", [False])
async def test_pairing_begin_raises_missing_pin_when_device_does_not_provide(
    pairing_handler,
):
    with pytest.raises(exceptions.InvalidStateError):
        await pairing_handler.begin()

    assert pairing_handler.state == PairingState.Failed
    assert pairing_handler.has_paired == False


@pytest.mark.parametrize("device_provides_pin", [False])
async def test_pairing_pair_success_when_device_does_not_provide_pin(
    pairing_handler, pairing_service
):
    pairing_handler.pin("1234")
    await pairing_handler.begin()
    await pairing_handler.finish()

    assert pairing_handler.state == PairingState.Finished
    assert pairing_handler.has_paired == True
    assert pairing_service.credentials == "1234"
