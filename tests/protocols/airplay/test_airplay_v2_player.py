"""Unit tests for AirPlay 2 URL playback."""

# pylint: disable=protected-access

import plistlib
from unittest.mock import AsyncMock, MagicMock

import pytest

from pyatv import exceptions
from pyatv.protocols.airplay.channels import EventChannel
from pyatv.protocols.airplay.player import EVENT_WAIT_RETRIES, AirPlayPlayer
from pyatv.protocols.raop.protocols import StreamContext
from pyatv.protocols.raop.protocols.airplayv2 import AirPlayV2
from pyatv.support.http import HttpRequest, HttpResponse
from pyatv.support.rtsp import HTTP_PROTOCOL, RtspSession

STREAM = "https://example.com/video.mp4"
START_POSITION = 2.5

pytestmark = pytest.mark.asyncio


def response(code: int = 200, body: bytes = b"") -> HttpResponse:
    """Create a minimal HTTP response."""
    return HttpResponse(HTTP_PROTOCOL, "1.1", code, "OK", {}, body)


async def test_url_commands_use_stream_specific_headers() -> None:
    rtsp = MagicMock(spec=RtspSession)
    rtsp.info = AsyncMock(return_value={})
    rtsp.record = AsyncMock(return_value=response())
    rtsp.setup = AsyncMock(
        return_value=response(
            body=plistlib.dumps({"streams": [{"streamID": 7}]}, fmt=plistlib.FMT_BINARY)
        )
    )
    rtsp.exchange = AsyncMock(return_value=response())

    protocol = AirPlayV2(StreamContext(), rtsp)
    protocol._verifier = MagicMock()
    result = await protocol.play_url(49152, STREAM, START_POSITION)

    assert result.code == 200
    assert rtsp.exchange.await_count == 4
    commands = []
    for call in rtsp.exchange.await_args_list:
        assert call.kwargs["uri"] == "/command"
        assert call.kwargs["protocol"] == HTTP_PROTOCOL
        assert call.kwargs["headers"]["X-Apple-StreamID"] == 7
        commands.append(plistlib.loads(call.kwargs["body"]["params"]["data"]))

    assert [command["type"] for command in commands] == [
        "insertPlayQueueItem",
        "setProperty",
        "setProperty",
        "setRate",
    ]
    assert commands[0]["item"]["Content-Location"] == STREAM
    assert commands[0]["item"]["Start-Position-Seconds"] == START_POSITION


async def test_url_command_failure_stops_sequence() -> None:
    rtsp = MagicMock(spec=RtspSession)
    rtsp.info = AsyncMock(return_value={})
    rtsp.record = AsyncMock(return_value=response())
    rtsp.setup = AsyncMock(
        return_value=response(
            body=plistlib.dumps({"streams": [{"streamID": 3}]}, fmt=plistlib.FMT_BINARY)
        )
    )
    rtsp.exchange = AsyncMock(return_value=response(500))

    protocol = AirPlayV2(StreamContext(), rtsp)
    protocol._verifier = MagicMock()
    result = await protocol.play_url(49152, STREAM)

    assert result.code == 500
    assert rtsp.exchange.await_count == 1


async def test_missing_url_control_stream_is_protocol_error() -> None:
    rtsp = MagicMock(spec=RtspSession)
    rtsp.info = AsyncMock(return_value={})
    rtsp.record = AsyncMock(return_value=response())
    rtsp.setup = AsyncMock(return_value=response(body=plistlib.dumps({"streams": []})))

    protocol = AirPlayV2(StreamContext(), rtsp)
    protocol._verifier = MagicMock()

    with pytest.raises(exceptions.ProtocolError):
        await protocol.play_url(49152, STREAM)


async def test_event_channel_decodes_nested_playback_state() -> None:
    channel = EventChannel(b"0" * 32, b"1" * 32)
    events = []
    channel.set_event_listener(events.append)
    event = {"type": "playbackState", "params": {"playbackState": "playing"}}
    body = plistlib.dumps(
        {"params": {"data": plistlib.dumps(event, fmt=plistlib.FMT_BINARY)}},
        fmt=plistlib.FMT_BINARY,
    )

    channel._process_event(HttpRequest("POST", "/event", "HTTP", "1.1", {}, body))

    assert events == [event]


async def test_airplay_v2_tracks_named_playback_state() -> None:
    protocol = AirPlayV2(StreamContext(), MagicMock(spec=RtspSession))

    protocol._handle_event({"type": "playbackState", "name": "playing"})

    assert protocol.playback_state == "playing"


async def test_airplay_v2_tracks_parameterized_playback_state() -> None:
    protocol = AirPlayV2(StreamContext(), MagicMock(spec=RtspSession))

    protocol._handle_event(
        {
            "type": "playbackState",
            "name": "playing",
            "params": {"playbackState": "stopped"},
        }
    )

    assert protocol.playback_state == "stopped"


async def test_airplay_v2_ignores_duplicate_playback_state() -> None:
    protocol = AirPlayV2(StreamContext(), MagicMock(spec=RtspSession))
    event = {"type": "playbackState", "name": "loading"}
    protocol._handle_event(event)
    protocol._playback_state_changed.clear()

    protocol._handle_event(event)

    assert not protocol._playback_state_changed.is_set()


async def test_player_waits_for_event_state_until_stopped() -> None:
    stream = MagicMock()
    stream.playback_state = None
    stream.wait_for_playback_state_change = AsyncMock(
        side_effect=["playing", "stopped"]
    )
    airplay_player = AirPlayPlayer(MagicMock(), stream)

    await airplay_player._wait_for_media_to_end_from_events()

    assert stream.wait_for_playback_state_change.await_count == 2


async def test_player_fails_when_event_state_never_starts() -> None:
    stream = MagicMock()
    stream.playback_state = None
    stream.wait_for_playback_state_change = AsyncMock(return_value=None)
    airplay_player = AirPlayPlayer(MagicMock(), stream)

    with pytest.raises(exceptions.PlaybackError, match="did not start"):
        await airplay_player._wait_for_media_to_end_from_events()

    assert stream.wait_for_playback_state_change.await_count == EVENT_WAIT_RETRIES
