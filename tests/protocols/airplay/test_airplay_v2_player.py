"""Unit tests for AirPlay 2 URL playback."""

# pylint: disable=protected-access

import asyncio
import plistlib
from typing import Dict, List, Mapping, Tuple
from unittest.mock import AsyncMock, MagicMock

import aiohttp
import pytest
from pytest_httpserver import HTTPServer

from pyatv import exceptions
from pyatv.protocols.airplay.channels import EventChannel
from pyatv.protocols.airplay.player import EVENT_WAIT_RETRIES, AirPlayPlayer
from pyatv.protocols.raop.protocols import StreamContext, airplayv2
from pyatv.protocols.raop.protocols.airplayv2 import (
    FCUP_FETCH_FAILED,
    AirPlayV2,
    UrlFetchResult,
    fetch_unhandled_url,
)
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
    stream.url_load_error = None
    stream.wait_for_playback_state_change = AsyncMock(
        side_effect=["playing", "stopped"]
    )
    airplay_player = AirPlayPlayer(MagicMock(), stream)

    await airplay_player._wait_for_media_to_end_from_events()

    assert stream.wait_for_playback_state_change.await_count == 2


async def test_player_fails_when_event_state_never_starts() -> None:
    stream = MagicMock()
    stream.playback_state = None
    stream.url_load_error = None
    stream.wait_for_playback_state_change = AsyncMock(return_value=None)
    airplay_player = AirPlayPlayer(MagicMock(), stream)

    with pytest.raises(exceptions.PlaybackError, match="did not start"):
        await airplay_player._wait_for_media_to_end_from_events()

    assert stream.wait_for_playback_state_change.await_count == EVENT_WAIT_RETRIES


async def test_player_fails_fast_when_url_cannot_be_loaded() -> None:
    stream = MagicMock()
    stream.playback_state = "loading"
    stream.url_load_error = "https://example.com/a.mp4 returned HTTP 403"
    stream.wait_for_playback_state_change = AsyncMock(return_value="loading")
    airplay_player = AirPlayPlayer(MagicMock(), stream)

    with pytest.raises(exceptions.PlaybackError, match="HTTP 403"):
        await airplay_player._wait_for_media_to_end_from_events()

    stream.wait_for_playback_state_change.assert_not_awaited()


PLAYLIST_URL = "https://example.com/master.m3u8"
PLAYLIST = b"#EXTM3U\n#EXT-X-ENDLIST\n"


def unhandled_url_event(message_id: str = "1") -> Dict:
    """Return an unhandledURL request as sent by tvOS 27 on the event channel."""
    return {
        "kind": "request",
        "type": "unhandledURL",
        "messageID": message_id,
        "request": {
            "FCUP_Response_URL": PLAYLIST_URL,
            "FCUP_Response_RequestID": 4,
            "FCUP_Response_IsContentKeyRequest": False,
            "FCUP_Response_Headers": {
                "User-Agent": "AppleCoreMedia/1.0.0.980.77.2",
                "Accept-Encoding": "gzip",
            },
        },
    }


def url_protocol() -> Tuple[AirPlayV2, AsyncMock]:
    """Return a protocol with a URL control stream and a mocked exchange."""
    rtsp = MagicMock(spec=RtspSession)
    rtsp.exchange = AsyncMock(return_value=response())
    protocol = AirPlayV2(StreamContext(), rtsp)
    protocol._stream_id = 7
    return protocol, rtsp.exchange


async def finish_fcup(protocol: AirPlayV2) -> None:
    """Wait for the background tasks answering unhandledURL requests."""
    await asyncio.gather(*list(protocol._fcup_tasks))


async def test_unhandled_url_request_is_fetched_and_answered() -> None:
    protocol, exchange = url_protocol()
    fetched: List[Tuple[str, Mapping[str, str]]] = []

    async def fetcher(url: str, headers: Mapping[str, str]) -> UrlFetchResult:
        fetched.append((url, headers))
        return 200, {"Content-Type": "application/vnd.apple.mpegurl"}, PLAYLIST

    protocol.url_fetcher = fetcher
    protocol._handle_event(unhandled_url_event("9"))
    await finish_fcup(protocol)

    # Accept-Encoding is left to the HTTP client, which decodes the body
    assert fetched == [(PLAYLIST_URL, {"User-Agent": "AppleCoreMedia/1.0.0.980.77.2"})]
    assert exchange.await_count == 1
    call = exchange.await_args
    assert call.kwargs["uri"] == "/command"
    assert call.kwargs["headers"]["X-Apple-StreamID"] == 7
    assert plistlib.loads(call.kwargs["body"]["params"]["data"]) == {
        "kind": "response",
        "messageID": "9",
        "type": "unhandledURL",
        "response": {
            "FCUP_Response_URL": PLAYLIST_URL,
            "FCUP_Response_RequestID": 4,
            "FCUP_Response_StatusCode": 200,
            "FCUP_Response_Headers": {"Content-Type": "application/vnd.apple.mpegurl"},
            "FCUP_Response_Data": PLAYLIST,
        },
    }
    assert protocol.playback_state is None
    assert protocol.url_load_error is None


async def test_unhandled_url_fetch_failure_is_reported_to_receiver() -> None:
    protocol, exchange = url_protocol()
    protocol.url_fetcher = AsyncMock(side_effect=aiohttp.ClientError("refused"))

    protocol._handle_event(unhandled_url_event())
    await finish_fcup(protocol)

    reply = plistlib.loads(exchange.await_args.kwargs["body"]["params"]["data"])
    assert reply["response"]["FCUP_Response_StatusCode"] == FCUP_FETCH_FAILED
    assert reply["response"]["FCUP_Response_Data"] == b""
    assert protocol.url_load_error is not None
    assert PLAYLIST_URL in protocol.url_load_error
    assert protocol._playback_state_changed.is_set()


async def test_unhandled_url_error_status_is_passed_on_and_recorded() -> None:
    protocol, exchange = url_protocol()
    protocol.url_fetcher = AsyncMock(return_value=(403, {}, b"denied"))

    protocol._handle_event(unhandled_url_event())
    await finish_fcup(protocol)

    reply = plistlib.loads(exchange.await_args.kwargs["body"]["params"]["data"])
    assert reply["response"]["FCUP_Response_StatusCode"] == 403
    assert reply["response"]["FCUP_Response_Data"] == b"denied"
    assert protocol.url_load_error == f"{PLAYLIST_URL} returned HTTP 403"


@pytest.mark.parametrize("missing", ["messageID", "request"])
async def test_malformed_unhandled_url_request_is_ignored(missing: str) -> None:
    protocol, exchange = url_protocol()
    protocol.url_fetcher = AsyncMock()
    event = unhandled_url_event()
    del event[missing]

    protocol._handle_event(event)
    await finish_fcup(protocol)

    protocol.url_fetcher.assert_not_awaited()
    exchange.assert_not_awaited()


async def test_teardown_cancels_pending_unhandled_url_requests() -> None:
    protocol, exchange = url_protocol()
    started = asyncio.Event()

    async def fetcher(  # pylint: disable=unused-argument
        url: str, headers: Mapping[str, str]
    ) -> UrlFetchResult:
        started.set()
        await asyncio.Event().wait()
        raise AssertionError("not reached")

    protocol.url_fetcher = fetcher
    protocol._handle_event(unhandled_url_event())
    task = next(iter(protocol._fcup_tasks))
    await started.wait()

    protocol.teardown()

    with pytest.raises(asyncio.CancelledError):
        await task
    exchange.assert_not_awaited()


async def test_fetch_unhandled_url_returns_decoded_response(
    httpserver: HTTPServer,
) -> None:
    httpserver.expect_request(
        "/master.m3u8", headers={"User-Agent": "AppleCoreMedia"}
    ).respond_with_data(PLAYLIST, content_type="application/vnd.apple.mpegurl")

    status, headers, data = await fetch_unhandled_url(
        httpserver.url_for("/master.m3u8"), {"User-Agent": "AppleCoreMedia"}
    )

    assert (status, data) == (200, PLAYLIST)
    assert headers["Content-Type"] == "application/vnd.apple.mpegurl"
    assert headers["Content-Length"] == str(len(PLAYLIST))


async def test_fetch_unhandled_url_passes_error_status(httpserver: HTTPServer) -> None:
    httpserver.expect_request("/denied").respond_with_data(b"no", status=403)

    status, _, data = await fetch_unhandled_url(httpserver.url_for("/denied"), {})

    assert (status, data) == (403, b"no")


async def test_fetch_unhandled_url_refuses_large_response(
    httpserver: HTTPServer, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(airplayv2, "FCUP_MAX_RESPONSE_SIZE", 4)
    httpserver.expect_request("/big").respond_with_data(b"12345")

    with pytest.raises(exceptions.ProtocolError):
        await fetch_unhandled_url(httpserver.url_for("/big"), {})
