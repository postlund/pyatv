import asyncio
from typing import Any, Mapping, cast
from unittest.mock import Mock

import pytest

from pyatv.const import KeyboardFocusState
from pyatv.core import Core, MessageDispatcher, ProtocolStateDispatcher, UpdatedState
from pyatv.protocols.companion import CompanionKeyboard

pytestmark = pytest.mark.asyncio


class CompanionApiMock(MessageDispatcher[str, Mapping[str, Any]]):
    async def inject(self, event_name: str, data: Mapping[str, Any]) -> None:
        await asyncio.gather(*self.dispatch(event_name, data))


class CompanionCoreMock:
    def __init__(
        self,
        state_dispatcher: ProtocolStateDispatcher,
    ) -> None:
        self.state_dispatcher = state_dispatcher


@pytest.fixture(name="api_mock")
def api_mock_fixture(event_loop):
    yield CompanionApiMock()


@pytest.fixture(name="keyboard")
def audio_fixture(api_mock, companion_state_dispatcher):
    yield CompanionKeyboard(
        api_mock, cast(Core, CompanionCoreMock(companion_state_dispatcher))
    )


@pytest.mark.parametrize(
    "event,data,expected_volume",
    [
        ("_tiStarted", {"_tiD": b""}, KeyboardFocusState.Focused),
        ("_tiStopped", {}, KeyboardFocusState.Unfocused),
    ],
)
async def test_keyboard_handle_text_input_dispatches(
    api_mock,
    keyboard,
    companion_state_dispatcher,
    event,
    data,
    expected_volume,
):
    callback = Mock()
    companion_state_dispatcher.listen_to(UpdatedState.KeyboardFocus, callback)

    await api_mock.inject(event, data)

    assert callback.called is True
    message = callback.call_args.args[0]
    assert message.value == expected_volume
