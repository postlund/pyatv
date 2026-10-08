"""Native AirPlay relay transport and public control API tests."""

import asyncio
from ipaddress import ip_address
import plistlib
from unittest.mock import AsyncMock, Mock

import pytest
import pytest_asyncio

import pyatv
from pyatv import exceptions
from pyatv.auth.hap_pairing import TRANSIENT_CREDENTIALS
from pyatv.conf import AppleTV
from pyatv.const import DeviceState, FeatureName, FeatureState, Protocol
from pyatv.core import MutableService
from pyatv.protocols.airplay import relay
from pyatv.protocols.airplay.channels import BaseDataStreamChannel
from pyatv.protocols.airplay.relay import RelayConnection, RelayEvents
from pyatv.protocols.mrp import messages, protobuf
from pyatv.settings import MrpTunnel, Settings
from pyatv.storage.memory_storage import MemoryStorage
from pyatv.support.http import HttpRequest, HttpResponse, format_request, parse_response


def player_path(bundle="selected"):
    path = protobuf.PlayerPath()
    path.origin.identifier = 1
    path.client.bundleIdentifier = bundle
    path.client.processIdentifier = 42
    path.player.identifier = "MediaRemote-DefaultPlayer"
    return path


def selected_state(
    bundle="selected", state=protobuf.PlaybackState.Playing, artwork_available=False
):
    msg = messages.create(protobuf.SET_STATE_MESSAGE)
    inner = protobuf.extract_inner(msg)
    inner.playerPath.CopyFrom(player_path(bundle))
    inner.playbackState = state
    inner.playbackQueue.location = 0
    item = inner.playbackQueue.contentItems.add()
    item.identifier = "item"
    item.metadata.title = "Song"
    item.metadata.trackArtistName = "Artist"
    item.metadata.albumName = "Album"
    item.metadata.duration = 300
    item.metadata.elapsedTime = 30
    item.metadata.elapsedTimeTimestamp = 1
    if artwork_available:
        item.metadata.artworkAvailable = True
        item.metadata.artworkMIMEType = "image/jpeg"
        item.metadata.artworkIdentifier = "artwork-item"
    for command in (1, 2, 3, 5, 6, 45):
        info = inner.supportedCommands.supportedCommands.add()
        info.command = command
        info.enabled = True
    return msg


@pytest.mark.asyncio
async def test_event_fragments_acknowledgments_batch_and_stream_filter():
    queue = asyncio.Queue()
    channel = RelayEvents(bytes(32), bytes(32), queue)
    channel.stream_id = 7
    channel.send = Mock()
    message = selected_state()
    data = BaseDataStreamChannel.encode_protobufs([message, message])
    body = plistlib.dumps({"params": {"data": data}}, fmt=plistlib.FMT_BINARY)
    request = HttpRequest(
        "POST",
        "/command",
        "RTSP",
        "1.0",
        {
            "Content-Type": "application/x-apple-binary-plist",
            "CSeq": "123",
            "X-Apple-StreamID": "7",
        },
        body,
    )
    wire = format_request(request)
    channel.buffer = wire[:20]
    channel.handle_received()
    channel.send.assert_not_called()
    channel.buffer += wire[20:] + wire
    channel.handle_received()
    assert queue.qsize() == 4
    assert channel.send.call_count == 2
    response, rest = parse_response(channel.send.call_args.args[0])
    assert not rest and response.code == 200 and response.headers["CSeq"] == "123"
    channel.buffer = wire.replace(b"StreamID: 7", b"StreamID: 8")
    channel.handle_received()
    assert channel.send.call_count == 3 and queue.qsize() == 4
    for _ in range(4):
        queue.get_nowait()
    channel.connection_lost(None)
    assert isinstance(queue.get_nowait(), EOFError)


@pytest.fixture
def core():
    return Mock(
        config=Mock(address="192.0.2.10"), service=Mock(port=7000), settings=Settings()
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("dedicated", [False, True])
async def test_native_sequence_negotiated_stream_and_cleanup(
    monkeypatch, core, dedicated
):
    conn = RelayConnection(core, TRANSIENT_CREDENTIALS)
    http = Mock(remote_ip="192.0.2.10")
    monkeypatch.setattr(relay, "http_connect", AsyncMock(return_value=http))
    monkeypatch.setattr(relay, "verify_connection", AsyncMock())
    events = RelayEvents(bytes(32), bytes(32), conn.queue)
    events.close = Mock()
    channel = AsyncMock(return_value=(Mock(), events))
    monkeypatch.setattr(relay, "setup_channel", channel)
    requests = []
    stream = {"type": 130, "streamID": 7}
    if dedicated:
        stream["dataPort"] = 1234

    async def exchange(method, path=None, **kwargs):
        requests.append((method, path, kwargs))
        response = (
            {"streams": [stream]}
            if "streams" in kwargs.get("body", {})
            else {"eventPort": 1234}
        )
        return HttpResponse("RTSP", "1.0", 200, "OK", {}, plistlib.dumps(response))

    conn.exchange = AsyncMock(side_effect=exchange)
    try:
        if dedicated:
            with pytest.raises(exceptions.InvalidResponseError, match="two-channel"):
                await conn.connect()
        else:
            await conn.connect()
            assert conn.connected and conn.stream_id == events.stream_id == 7
        assert [(method, path) for method, path, _ in requests] == [
            ("GET", "/info"),
            ("POST", "/auth-setup"),
            ("SETUP", None),
            ("GET", "/info"),
            ("RECORD", None),
            ("SETUP", None),
        ]
        assert requests[1][2]["headers"] == {"X-Apple-AT": "16"}
        assert requests[1][2]["body"] == {"ascm": 1, "tkrd": ["pair", "auth", "uuid"]}
        assert requests[2][2]["body"]["isRemoteControlOnly"]
        assert requests[-1][2]["body"]["streams"][0]["controlType"] == 1
        assert "seed" not in requests[-1][2]["body"]["streams"][0]
        assert channel.call_args.args[-3:] == (
            "Events-Salt",
            "Events-Read-Encryption-Key",
            "Events-Write-Encryption-Key",
        )
    finally:
        conn.close()
        await conn.close_task
    assert requests[-1][0] == "TEARDOWN"
    assert not conn.connected
    http.close.assert_called_once()
    events.close.assert_called_once()


@pytest.mark.asyncio
async def test_authentication_failure_does_not_teardown_unestablished_session(
    monkeypatch, core
):
    conn = RelayConnection(core, TRANSIENT_CREDENTIALS)
    http = Mock()
    monkeypatch.setattr(relay, "http_connect", AsyncMock(return_value=http))
    monkeypatch.setattr(
        relay,
        "verify_connection",
        AsyncMock(side_effect=exceptions.AuthenticationError("rejected")),
    )
    conn.exchange = AsyncMock()
    try:
        with pytest.raises(exceptions.AuthenticationError):
            await conn.connect()
    finally:
        conn.close()
        await conn.close_task
    assert [call.args[0] for call in conn.exchange.call_args_list] == ["GET"]
    http.close.assert_called_once()


class Receiver:
    """Mock network boundary while retaining the real public API and protobufs."""

    def __init__(self):
        self.messages = []
        self.connection = None
        self.uid = "02:00:00:00:00:01"
        self.reject = None
        self.disconnected = False
        self.confirm_volume = True
        self.artwork_available = False
        self.artwork_data = b"synthetic-artwork"

    def volume(self, level, uid=None):
        message = messages.create(protobuf.VOLUME_DID_CHANGE_MESSAGE)
        inner = protobuf.extract_inner(message)
        inner.outputDeviceUID = uid or self.uid
        inner.volume = level
        return message

    async def exchange(self, connection, method, path=None, **kwargs):
        self.connection = connection
        body = kwargs.get("body", {})
        reply = {}
        if method == "SETUP":
            reply = (
                {"streams": [{"type": 130, "streamID": 7}]}
                if "streams" in body
                else {"eventPort": 1234}
            )
        elif method == "TEARDOWN":
            self.disconnected = True
        elif path == "/command":
            message = BaseDataStreamChannel.decode_protobufs(body["params"]["data"])[0]
            self.messages.append(message)
            response = messages.create(
                protobuf.GENERIC_MESSAGE, identifier=message.identifier
            )
            if message.type == protobuf.DEVICE_INFO_MESSAGE:
                response = messages.create(
                    protobuf.DEVICE_INFO_MESSAGE, identifier=message.identifier
                )
                info = protobuf.extract_inner(response)
                info.deviceUID = "sender-uid"
                info.name = "Sender"
                for uid, name in (
                    (self.uid, "Receiver"),
                    ("02:00:00:00:00:02", "Other"),
                ):
                    member = info.groupedDevices.add()
                    member.deviceUID = uid
                    member.name = name
            elif message.type == protobuf.CLIENT_UPDATES_CONFIG_MESSAGE:
                select = messages.create(protobuf.SET_NOW_PLAYING_CLIENT_MESSAGE)
                protobuf.extract_inner(select).client.CopyFrom(player_path().client)
                for update in (
                    select,
                    selected_state(artwork_available=self.artwork_available),
                    selected_state("inactive", 2),
                    self.volume(0.25),
                ):
                    connection.queue.put_nowait(update)
            elif message.type == protobuf.PLAYBACK_QUEUE_REQUEST_MESSAGE:
                response = selected_state(artwork_available=self.artwork_available)
                response.identifier = message.identifier
                item = protobuf.extract_inner(response).playbackQueue.contentItems[0]
                item.artworkData = self.artwork_data
                item.artworkDataWidth = 600
                item.artworkDataHeight = 600
            elif message.type == protobuf.SEND_COMMAND_MESSAGE:
                response = messages.command_result(message.identifier)
                if self.reject == "envelope":
                    response.errorCode = 1
                elif self.reject:
                    result = protobuf.extract_inner(response)
                    if self.reject == "status":
                        result.commandResult.statuses.add().statusCode = 1
                    elif self.reject == "nested":
                        result.commandResult.sendError = 1
                    else:
                        setattr(result, self.reject, 1)
            elif message.type == protobuf.SET_VOLUME_MESSAGE:
                inner = protobuf.extract_inner(message)
                # An unrelated group update must not confirm the requested change.
                connection.queue.put_nowait(self.volume(0.1, "02:00:00:00:00:02"))
                if self.confirm_volume:
                    connection.queue.put_nowait(
                        self.volume(inner.volume, inner.outputDeviceUID)
                    )
            if message.identifier:
                connection.queue.put_nowait(response)
        return HttpResponse("RTSP", "1.0", 200, "OK", {}, plistlib.dumps(reply))


@pytest_asyncio.fixture
async def connected_receiver(monkeypatch, request):
    receiver = Receiver()
    receiver.artwork_available = getattr(request, "param", False)
    monkeypatch.setattr(
        relay, "http_connect", AsyncMock(return_value=Mock(remote_ip="192.0.2.10"))
    )
    monkeypatch.setattr(relay, "verify_connection", AsyncMock())

    async def channel(factory, *args):
        event = factory(bytes(32), bytes(32))
        event.close = Mock()
        return Mock(), event

    async def exchange(connection, *args, **kwargs):
        return await receiver.exchange(connection, *args, **kwargs)

    monkeypatch.setattr(relay, "setup_channel", channel)
    monkeypatch.setattr(RelayConnection, "exchange", exchange)
    config = AppleTV(ip_address("192.0.2.10"), "Receiver")
    config.add_service(
        MutableService(
            "receiver",
            Protocol.AirPlay,
            7000,
            {"features": "0xC05F8A00,0x1C340", "deviceid": receiver.uid},
        )
    )
    storage = MemoryStorage()
    settings = await storage.get_settings(config)
    settings.protocols.airplay.mrp_tunnel = MrpTunnel.Relay
    atv = await pyatv.connect(config, asyncio.get_running_loop(), storage=storage)
    yield atv, receiver
    await asyncio.gather(*atv.close())
    assert receiver.disconnected
    assert all(task.done() for task in receiver.connection.tasks)


@pytest.mark.asyncio
async def test_public_api_metadata_native_subscription_and_scoped_selection(
    connected_receiver,
):
    atv, receiver = connected_receiver
    playing = await atv.metadata.playing()
    assert (
        playing.title == "Song"
        and playing.artist == "Artist"
        and playing.album == "Album"
    )
    assert playing.device_state == DeviceState.Playing
    assert [message.type for message in receiver.messages] == [15, 38, 16]
    info = protobuf.extract_inner(receiver.messages[0])
    assert not info.allowsPairing and info.supportsSharedQueue
    assert info.deviceClass == protobuf.DeviceClass.Mac
    updates = protobuf.extract_inner(receiver.messages[2])
    assert (
        updates.artworkUpdates and updates.volumeUpdates and updates.outputDeviceUpdates
    )
    assert not updates.keyboardUpdates and not updates.nowPlayingUpdates
    assert b"\x30\x00" in updates.SerializeToString()
    assert atv.features.get_feature(FeatureName.Pause).state == FeatureState.Available
    assert atv.features.get_feature(FeatureName.Home).state == FeatureState.Unsupported
    assert atv.audio.volume == 25
    assert len(atv.audio.output_devices) == 2


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "action,command",
    [
        ("play", 1),
        ("pause", 2),
        ("play_pause", 3),
        ("next", 5),
        ("previous", 6),
        ("set_position", 45),
    ],
)
async def test_public_playback_commands_target_selected_player(
    connected_receiver, action, command
):
    atv, receiver = connected_receiver
    (
        await getattr(atv.remote_control, action)(90)
        if action == "set_position"
        else await getattr(atv.remote_control, action)()
    )
    inner = protobuf.extract_inner(receiver.messages[-1])
    assert inner.command == command
    assert inner.playerPath == player_path()
    if action == "set_position":
        assert inner.options.playbackPosition == 90 and inner.options.sendOptions == 0


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "rejected", ["sendError", "handlerReturnStatus", "nested", "status", "envelope"]
)
async def test_public_control_rejection_is_not_reported_as_success(
    connected_receiver, rejected
):
    atv, receiver = connected_receiver
    receiver.reject = rejected
    with pytest.raises(exceptions.CommandError):
        await atv.remote_control.pause()


@pytest.mark.asyncio
async def test_public_volume_targets_receiver_or_explicit_group_member(
    connected_receiver,
):
    atv, receiver = connected_receiver
    await atv.audio.set_volume(50)
    assert atv.audio.volume == 50
    inner = protobuf.extract_inner(receiver.messages[-1])
    assert inner.outputDeviceUID == receiver.uid and inner.volume == 0.5
    other = atv.audio.output_devices[1]
    await atv.audio.set_volume(40, other)
    inner = protobuf.extract_inner(receiver.messages[-1])
    assert inner.outputDeviceUID == other.identifier
    assert inner.volume == pytest.approx(0.4)
    assert atv.audio.volume == 50


@pytest.mark.asyncio
@pytest.mark.parametrize("value", [-1, float("nan"), float("inf")])
async def test_invalid_seek_is_rejected_before_sending(connected_receiver, value):
    atv, receiver = connected_receiver
    before = len(receiver.messages)
    with pytest.raises(exceptions.CommandError):
        await atv.remote_control.set_position(value)
    assert len(receiver.messages) == before


@pytest.mark.asyncio
async def test_missing_player_path_is_rejected_before_sending(connected_receiver):
    atv, receiver = connected_receiver
    receiver.connection.paths.clear()
    before = len(receiver.messages)
    with pytest.raises(exceptions.InvalidStateError):
        await atv.remote_control.pause()
    assert len(receiver.messages) == before


@pytest.mark.asyncio
async def test_unrelated_group_volume_does_not_confirm_receiver_change(
    connected_receiver, monkeypatch
):
    atv, receiver = connected_receiver
    receiver.confirm_volume = False
    original_timeout = relay.async_timeout
    monkeypatch.setattr(relay, "async_timeout", lambda _: original_timeout(0.05))
    with pytest.raises(asyncio.TimeoutError):
        await atv.audio.set_volume(50)
    assert atv.audio.volume == 25


@pytest.mark.asyncio
async def test_missing_receiver_uid_never_falls_back_to_sender(connected_receiver):
    atv, receiver = connected_receiver
    for device in atv.audio.output_devices:
        device.identifier = "unknown"
    before = len(receiver.messages)
    with pytest.raises(exceptions.InvalidStateError):
        await atv.audio.set_volume(50)
    assert len(receiver.messages) == before


@pytest.mark.asyncio
@pytest.mark.parametrize("connected_receiver", [False, True], indirect=True)
async def test_public_artwork_availability_retrieval_cache_and_track_change(
    connected_receiver,
):
    atv, receiver = connected_receiver
    available = receiver.artwork_available
    assert atv.features.get_feature(FeatureName.Artwork).state == (
        FeatureState.Available if available else FeatureState.Unavailable
    )
    artwork = await atv.metadata.artwork(width=512)
    requests = [
        message
        for message in receiver.messages
        if message.type == protobuf.PLAYBACK_QUEUE_REQUEST_MESSAGE
    ]
    if not available:
        assert artwork is None and not requests
        return
    assert artwork.bytes == receiver.artwork_data
    assert artwork.mimetype == "image/jpeg"
    assert (artwork.width, artwork.height) == (600, 600)
    assert len(requests) == 1
    request = protobuf.extract_inner(requests[0])
    assert request.location == 0 and request.length == 1
    assert request.artworkWidth == 512
    assert request.returnContentItemAssetsInUserCompletion
    cached = await atv.metadata.artwork(width=512)
    assert cached == artwork
    assert len(receiver.messages) == 4  # Subscription plus one artwork request.

    update = selected_state(artwork_available=True)
    item = protobuf.extract_inner(update).playbackQueue.contentItems[0]
    item.identifier = "next-item"
    item.metadata.title = "Next song"
    item.metadata.artworkIdentifier = "artwork-next"
    receiver.artwork_data = b"synthetic-next-artwork"
    receiver.connection.queue.put_nowait(update)

    async def wait_for_track():
        while atv.metadata.artwork_id != "artwork-next":
            await asyncio.sleep(0)

    await asyncio.wait_for(wait_for_track(), 1)
    next_artwork = await atv.metadata.artwork(width=512)
    assert next_artwork.bytes == receiver.artwork_data
    assert next_artwork.bytes != artwork.bytes
    assert receiver.messages[-1].type == protobuf.PLAYBACK_QUEUE_REQUEST_MESSAGE
    assert len(receiver.messages) == 5
