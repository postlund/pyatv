"""Unit tests for AirPlay video v2 playback (receivers without /play)."""

import plistlib
from unittest.mock import AsyncMock, Mock

import pytest

from pyatv import exceptions
from pyatv.const import Protocol
from pyatv.core import MutableService
from pyatv.protocols.airplay import _video_v2_only
from pyatv.protocols.airplay.channels import EventChannel
from pyatv.protocols.airplay.player import AirPlayVideoV2Player
from pyatv.protocols.raop.protocols import StreamContext
from pyatv.protocols.raop.protocols.airplayv2 import (
    REMOTE_CONTROL_STREAM_TYPE,
    VIDEO_CLIENT_TYPE_UUID,
    AirPlayV2,
    decode_video_command,
)
from pyatv.support.http import HttpRequest, HttpResponse, format_request
from pyatv.support.rtsp import RtspSession

STREAM = "http://airplaystream"
RECEIVER_ID = "AA:BB:CC:DD:EE:FF"

pytestmark = pytest.mark.asyncio


def command_request(command, path="/command") -> HttpRequest:
    data = plistlib.dumps(command, fmt=plistlib.FMT_BINARY)
    body = plistlib.dumps({"params": {"data": data}}, fmt=plistlib.FMT_BINARY)
    return HttpRequest("POST", path, "RTSP", "1.0", {"CSeq": "1"}, body)


def response(code=200) -> HttpResponse:
    return HttpResponse("RTSP", "1.0", code, "OK", {}, b"")


class FakeVideoStream:
    """Stand-in for AirPlayV2 that replays receiver commands after setRate."""

    def __init__(self, rtsp, events=None, status=200, close_on_rate=False):
        self.rtsp = rtsp
        self.events = events or []
        self.status = status
        self.close_on_rate = close_on_rate
        self.commands = []
        self.receiver_id = None
        self.handler = None

    async def setup_video_stream(self, timing_server_port, receiver_id, handler):
        self.receiver_id = receiver_id
        self.handler = handler

    async def send_video_command(self, command):
        self.commands.append(command)
        if command["type"] == "setRate":
            for event in self.events:
                self.handler(event)
            if self.close_on_rate:
                self.rtsp.connection.close()
        return response(self.status)


@pytest.fixture(name="rtsp")
def rtsp_fixture(client_connection):
    yield RtspSession(client_connection)


async def play(rtsp, stream, position=0):
    await AirPlayVideoV2Player(rtsp, stream, RECEIVER_ID).play_url(STREAM, position)


async def test_play_queues_item_and_waits_for_end(rtsp):
    stream = FakeVideoStream(
        rtsp,
        events=[
            {"type": "playbackState", "name": "playing"},
            {"type": "notification", "name": "itemPlayedToEnd"},
        ],
    )

    await play(rtsp, stream, position=2.5)

    assert stream.receiver_id == RECEIVER_ID
    assert [command["type"] for command in stream.commands] == [
        "insertPlayQueueItem",
        "setProperty",
        "setRate",
    ]
    item = stream.commands[0]["item"]
    assert item["Content-Location"] == STREAM
    assert item["Start-Position"]["value"] == 2500000000
    assert item["Start-Position"]["timescale"] == 1000000000
    assert stream.commands[2]["rate"] == 1.0


@pytest.mark.parametrize(
    "url,position,media_type,start",
    [
        ("http://host/video.mp4", 0, "file", 0),
        ("http://host/live/index.m3u8?token=x", 0, "streaming", None),
        ("http://host/vod/index.M3U8", 1.5, "streaming", 1500000000),
    ],
)
async def test_play_media_type(rtsp, url, position, media_type, start):
    stream = FakeVideoStream(
        rtsp, events=[{"type": "notification", "name": "itemPlayedToEnd"}]
    )

    await AirPlayVideoV2Player(rtsp, stream, RECEIVER_ID).play_url(url, position)

    item = stream.commands[0]["item"]
    assert item["mediaType"] == media_type
    assert item.get("Start-Position", {}).get("value") == start


async def test_play_ends_when_receiver_stops(rtsp):
    stream = FakeVideoStream(
        rtsp, events=[{"type": "playbackState", "name": "stopped", "reason": "ended"}]
    )

    await play(rtsp, stream)


async def test_play_ends_when_connection_closed(rtsp):
    stream = FakeVideoStream(rtsp, close_on_rate=True)

    await play(rtsp, stream)


async def test_play_failed_item_raises(rtsp):
    stream = FakeVideoStream(
        rtsp, events=[{"type": "notification", "name": "itemFailedToPlayToEnd"}]
    )

    with pytest.raises(exceptions.PlaybackError):
        await play(rtsp, stream)


async def test_play_rejected_command_raises(rtsp):
    stream = FakeVideoStream(rtsp, status=400)

    with pytest.raises(exceptions.PlaybackError):
        await play(rtsp, stream)


@pytest.mark.parametrize(
    "request_,expected",
    [
        (
            command_request({"type": "setRate", "rate": 1.0}),
            {"type": "setRate", "rate": 1.0},
        ),
        (command_request({"type": "x"}, path="/feedback"), None),
        (HttpRequest("POST", "/command", "RTSP", "1.0", {}, b"garbage"), None),
        (HttpRequest("POST", "/command", "RTSP", "1.0", {}, b""), None),
    ],
)
async def test_decode_video_command(request_, expected):
    assert decode_video_command(request_) == expected


async def test_setup_video_stream_and_send_command():
    rtsp = Mock()
    rtsp.record = AsyncMock()
    rtsp.exchange = AsyncMock(return_value=response())
    rtsp.setup = AsyncMock(
        return_value=HttpResponse(
            "RTSP",
            "1.0",
            200,
            "OK",
            {},
            plistlib.dumps({"streams": [{"streamID": 7, "type": 130}]}),
        )
    )
    stream = AirPlayV2(StreamContext(), rtsp)
    stream._setup_base = AsyncMock()  # pylint: disable=protected-access
    stream.start_feedback = AsyncMock()
    stream.event_protocol = EventChannel(bytes(32), bytes(32))

    received = []
    await stream.setup_video_stream(1234, RECEIVER_ID, received.append)

    setup = rtsp.setup.call_args.kwargs["body"]["streams"][0]
    assert setup["type"] == REMOTE_CONTROL_STREAM_TYPE
    assert setup["controlType"] == 1
    assert setup["channelID"] == f"{RECEIVER_ID}-RCS-2"
    assert setup["clientTypeUUID"] == VIDEO_CLIENT_TYPE_UUID
    rtsp.record.assert_awaited_once()

    stream.event_protocol.request_handler(command_request({"type": "ping"}))
    assert received == [{"type": "ping"}]

    await stream.send_video_command({"type": "setRate", "rate": 0.0})
    kwargs = rtsp.exchange.call_args.kwargs
    assert kwargs["uri"] == "/command"
    assert kwargs["headers"] == {"X-Apple-StreamID": 7}
    assert plistlib.loads(kwargs["body"]["params"]["data"]) == {
        "type": "setRate",
        "rate": 0.0,
    }


async def test_send_video_command_requires_setup():
    stream = AirPlayV2(StreamContext(), Mock())

    with pytest.raises(exceptions.InvalidStateError):
        await stream.send_video_command({"type": "setRate", "rate": 1.0})


async def test_event_channel_passes_requests_to_handler():
    channel = EventChannel(bytes(32), bytes(32))
    channel.transport = Mock()
    received = []
    channel.request_handler = received.append
    channel.buffer = format_request(command_request({"type": "ping"}))

    channel.handle_received()

    assert len(received) == 1
    assert decode_video_command(received[0]) == {"type": "ping"}
    channel.transport.write.assert_called_once()


@pytest.mark.parametrize(
    "properties,expected",
    [
        ({"features": "0x00000000,0x00020000"}, True),
        ({"features": "0x00000001,0x00020000"}, False),
        ({"features": "0x00000001"}, False),
        ({}, False),
    ],
)
async def test_video_v2_only(properties, expected):
    service = MutableService("id", Protocol.AirPlay, 7000, properties)
    assert _video_v2_only(service) == expected
