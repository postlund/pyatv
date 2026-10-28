import asyncio
from typing import Any, Mapping, cast
from unittest.mock import AsyncMock, Mock

import pytest

from pyatv.const import KeyboardFocusState
from pyatv.core import Core, MessageDispatcher, ProtocolStateDispatcher, UpdatedState
from pyatv.protocols.companion import (
    CompanionAudio,
    CompanionKeyboard,
    MediaControlFlags,
)

pytestmark = pytest.mark.asyncio


class CompanionApiMock(MessageDispatcher[str, Mapping[str, Any]]):
    def __init__(self) -> None:
        super().__init__()
        self.mediacontrol_command = AsyncMock()

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


@pytest.fixture(name="audio")
def companion_audio_fixture(api_mock, companion_state_dispatcher):
    yield CompanionAudio(
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


async def test_audio_volume_control_available_dispatches_volume(
    api_mock, audio, companion_state_dispatcher
):
    api_mock.mediacontrol_command.return_value = {"_c": {"_vol": 0.4}}
    callback = Mock()
    companion_state_dispatcher.listen_to(UpdatedState.Volume, callback)

    await api_mock.inject("_iMC", {"_mcF": MediaControlFlags.Volume})

    assert audio.volume == 40.0
    assert callback.called is True
    assert callback.call_args.args[0].value == 40.0


async def test_audio_volume_control_unavailable_does_not_dispatch_volume(
    api_mock, audio, companion_state_dispatcher
):
    callback = Mock()
    companion_state_dispatcher.listen_to(UpdatedState.Volume, callback)

    # Volume is unknown when volume control is unavailable (e.g. Apple TV where the
    # TV controls the volume), so 0.0 must not be published as a real volume level.
    # Other protocols (like RAOP) trust dispatched volume and would mute playback.
    await api_mock.inject("_iMC", {"_mcF": 0})

    assert audio.volume == 0.0
    api_mock.mediacontrol_command.assert_not_called()
    assert callback.called is False
