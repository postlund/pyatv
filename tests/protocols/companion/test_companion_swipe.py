"""Tests for Companion touch gesture timing."""

from unittest.mock import patch

import pytest

from pyatv.const import TouchAction
from pyatv.protocols.companion.api import TOUCHPAD_DELAY_MS, CompanionAPI


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "coords",
    [
        (100, 500, 900, 500),
        (900, 500, 100, 500),
        (500, 100, 500, 900),
        (500, 900, 500, 100),
    ],
)
@pytest.mark.parametrize("duration", [1, 16, 100])
async def test_swipe_event_timing_and_bounds(coords, duration):
    now = 0
    events = []

    async def sleep(delay):
        nonlocal now
        now += int(delay * 1_000_000_000)

    async def event(x, y, action):
        events.append((now, x, y, action))

    with (
        patch("pyatv.protocols.companion.api.time.time_ns", side_effect=lambda: now),
        patch("pyatv.protocols.companion.api.asyncio.sleep", side_effect=sleep),
    ):
        api = CompanionAPI(None)
        with patch.object(api, "hid_event", side_effect=event):
            await api.swipe(*coords, duration)

    assert events[0] == (0, *coords[:2], TouchAction.Press)
    assert events[-1][1:] == (*coords[2:], TouchAction.Release)
    assert events[-1][0] >= duration * 1_000_000
    if duration > TOUCHPAD_DELAY_MS:
        assert any(action is TouchAction.Hold for _, _, _, action in events)
    for index, (timestamp, x, y, action) in enumerate(events[1:], 1):
        assert timestamp > events[index - 1][0]
        assert min(coords[0], coords[2]) <= x <= max(coords[0], coords[2])
        assert min(coords[1], coords[3]) <= y <= max(coords[1], coords[3])
        if action is TouchAction.Hold:
            assert timestamp - events[index - 1][0] >= TOUCHPAD_DELAY_MS * 1_000_000
