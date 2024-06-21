"""Unit tests for client and player management."""

from unittest.mock import MagicMock

import pytest

from pyatv.protocols.mrp import messages, player_state
from pyatv.protocols.mrp import protobuf as pb

CLIENT_ID_1 = "client_id_1"
CLIENT_NAME_1 = "client_name_1"

CLIENT_ID_2 = "client_id_2"

PLAYER_ID_1 = "player_id_1"
PLAYER_NAME_1 = "player_name_1"

DEFAULT_PLAYER = "MediaRemote-DefaultPlayer"

pytestmark = pytest.mark.asyncio


def set_path(
    message,
    client_id=CLIENT_ID_1,
    client_name=CLIENT_NAME_1,
    player_id=PLAYER_ID_1,
    player_name=PLAYER_NAME_1,
):
    client = message.inner().playerPath.client
    client.bundleIdentifier = client_id
    if client_name:
        client.displayName = client_name

    player = message.inner().playerPath.player
    player.identifier = player_id
    if player_name:
        player.displayName = player_name
    return message


def add_metadata_item(msg, location=0, identifier=None, **metadata_fields):
    queue = msg.inner().playbackQueue
    queue.location = location
    item = queue.contentItems.add()
    if identifier:
        item.identifier = identifier
    metadata = item.metadata
    for key, value in metadata_fields.items():
        setattr(metadata, key, value)
    return msg


@pytest.fixture
def listener(psm):
    class _StubListener:
        def __init__(self):
            self.call_count = 0

        async def state_updated(self):
            self.call_count += 1

    listener_mock = _StubListener()
    psm.listener = listener_mock
    yield listener_mock


@pytest.fixture
def psm(protocol_mock):
    yield player_state.PlayerStateManager(protocol_mock)


async def test_get_client_and_player(psm, protocol_mock):
    msg = set_path(messages.create(pb.SET_STATE_MESSAGE))
    await protocol_mock.inject(msg)

    player = psm.get_player(msg.inner().playerPath)
    assert player.identifier == PLAYER_ID_1
    assert player.display_name == PLAYER_NAME_1

    client = psm.get_client(msg.inner().playerPath.client)
    assert client.bundle_identifier == CLIENT_ID_1
    assert client.display_name == CLIENT_NAME_1


async def test_no_metadata(psm, protocol_mock):
    msg = set_path(messages.create(pb.SET_STATE_MESSAGE))
    await protocol_mock.inject(msg)

    player = psm.get_player(msg.inner().playerPath)
    assert player.metadata is None


async def test_metadata_single_item(psm, protocol_mock):
    msg = set_path(messages.create(pb.SET_STATE_MESSAGE))
    msg = add_metadata_item(msg, title="item")
    await protocol_mock.inject(msg)

    player = psm.get_player(msg.inner().playerPath)
    assert player.metadata.title == "item"


async def test_metadata_multiple_items(psm, protocol_mock):
    msg = set_path(messages.create(pb.SET_STATE_MESSAGE))
    msg = add_metadata_item(msg, title="item1")
    msg = add_metadata_item(msg, location=1, title="item2")
    await protocol_mock.inject(msg)

    player = psm.get_player(msg.inner().playerPath)
    assert player.metadata.title == "item2"


async def test_metadata_no_item_identifier(psm, protocol_mock):
    msg = set_path(messages.create(pb.SET_STATE_MESSAGE))
    await protocol_mock.inject(msg)

    player = psm.get_player(msg.inner().playerPath)
    assert player.item_identifier is None


async def test_metadata_item_identifier(psm, protocol_mock):
    msg = set_path(messages.create(pb.SET_STATE_MESSAGE))
    msg = add_metadata_item(msg, identifier="id1", title="item1")
    await protocol_mock.inject(msg)

    player = psm.get_player(msg.inner().playerPath)
    assert player.item_identifier == "id1"

    msg = add_metadata_item(msg, location=1, identifier="id2", title="item2")
    await protocol_mock.inject(msg)

    player = psm.get_player(msg.inner().playerPath)
    assert player.item_identifier == "id2"


async def test_get_metadata_field(psm, protocol_mock):
    msg = set_path(messages.create(pb.SET_STATE_MESSAGE))
    msg = add_metadata_item(msg, title="item", playCount=123)
    await protocol_mock.inject(msg)

    player = psm.get_player(msg.inner().playerPath)
    assert player.metadata_field("title") == "item"
    assert player.metadata_field("playCount") == 123


async def test_content_item_update(psm, protocol_mock):
    msg = set_path(messages.create(pb.SET_STATE_MESSAGE))
    msg = add_metadata_item(msg, identifier="id", title="item", playCount=123)
    await protocol_mock.inject(msg)

    msg = set_path(messages.create(pb.UPDATE_CONTENT_ITEM_MESSAGE))
    item = msg.inner().contentItems.add()
    item.identifier = "id"
    item.metadata.title = "new title"
    item.metadata.playCount = 1111
    await protocol_mock.inject(msg)

    player = psm.get_player(msg.inner().playerPath)
    assert player.metadata_field("title") == "new title"
    assert player.metadata_field("playCount") == 1111


async def test_get_command_info(psm, protocol_mock):
    msg = set_path(messages.create(pb.SET_STATE_MESSAGE))
    info = msg.inner().supportedCommands.supportedCommands.add()
    info.command = pb.CommandInfo_pb2.Pause
    await protocol_mock.inject(msg)

    player = psm.get_player(msg.inner().playerPath)
    assert player.command_info(pb.CommandInfo_pb2.Play) is None
    assert player.command_info(pb.CommandInfo_pb2.Pause) is not None


async def test_playback_state_without_rate(psm, protocol_mock):
    msg = set_path(messages.create(pb.SET_STATE_MESSAGE))
    msg.inner().playbackState = pb.PlaybackState.Paused
    msg = add_metadata_item(msg)
    await protocol_mock.inject(msg)

    player = psm.get_player(msg.inner().playerPath)
    assert player.playback_state is pb.PlaybackState.Paused

    msg.inner().playbackState = pb.PlaybackState.Playing
    await protocol_mock.inject(msg)

    player = psm.get_player(msg.inner().playerPath)
    assert player.playback_state is pb.PlaybackState.Playing


async def test_playback_state_playing(psm, protocol_mock):
    set_state = set_path(messages.create(pb.SET_STATE_MESSAGE))
    set_state.inner().playbackState = pb.PlaybackState.Playing
    msg = add_metadata_item(set_state, playbackRate=1.0)
    await protocol_mock.inject(msg)

    player = psm.get_player(msg.inner().playerPath)
    assert player.playback_state == pb.PlaybackState.Playing


async def test_playback_state_seeking(psm, protocol_mock):
    set_state = set_path(messages.create(pb.SET_STATE_MESSAGE))
    set_state.inner().playbackState = pb.PlaybackState.Playing
    msg = add_metadata_item(set_state, playbackRate=2.0)
    await protocol_mock.inject(msg)

    player = psm.get_player(msg.inner().playerPath)
    assert player.playback_state == pb.PlaybackState.Seeking


async def test_playback_state_playing_with_zero_playbac_rate(psm, protocol_mock):
    set_state = set_path(messages.create(pb.SET_STATE_MESSAGE))
    set_state.inner().playbackState = pb.PlaybackState.Playing
    msg = add_metadata_item(set_state, playbackRate=0.0)
    await protocol_mock.inject(msg)

    player = psm.get_player(msg.inner().playerPath)
    assert player.playback_state == pb.PlaybackState.Playing


async def test_change_listener(psm, listener):
    assert psm.listener == listener

    psm.listener = None
    assert psm.listener is None


async def test_set_now_playing_client(psm, protocol_mock, listener):
    msg = messages.create(pb.SET_NOW_PLAYING_CLIENT_MESSAGE)
    client = msg.inner().client
    client.bundleIdentifier = CLIENT_ID_1
    await protocol_mock.inject(msg)

    assert listener.call_count == 1

    assert psm.client.bundle_identifier == CLIENT_ID_1


async def test_set_now_playing_player_when_no_client(psm, protocol_mock, listener):
    msg = set_path(messages.create(pb.SET_NOW_PLAYING_PLAYER_MESSAGE))
    await protocol_mock.inject(msg)

    assert listener.call_count == 0

    assert not psm.playing.identifier
    assert not psm.playing.display_name


async def test_set_now_playing_player_for_active_client(psm, protocol_mock, listener):
    msg = messages.create(pb.SET_NOW_PLAYING_CLIENT_MESSAGE)
    client = msg.inner().client
    client.bundleIdentifier = CLIENT_ID_1
    await protocol_mock.inject(msg)

    msg = set_path(messages.create(pb.SET_NOW_PLAYING_PLAYER_MESSAGE))
    await protocol_mock.inject(msg)

    assert listener.call_count == 2

    assert psm.playing.identifier == PLAYER_ID_1
    assert psm.playing.display_name == PLAYER_NAME_1


async def test_default_player_when_only_client_set(psm, protocol_mock, listener):
    msg = set_path(messages.create(pb.SET_STATE_MESSAGE))
    await protocol_mock.inject(msg)
    msg = set_path(
        messages.create(pb.SET_STATE_MESSAGE),
        player_id=DEFAULT_PLAYER,
        player_name="Default Name",
    )
    await protocol_mock.inject(msg)

    msg = messages.create(pb.SET_NOW_PLAYING_CLIENT_MESSAGE)
    client = msg.inner().client
    client.bundleIdentifier = CLIENT_ID_1
    await protocol_mock.inject(msg)

    assert psm.playing.identifier == DEFAULT_PLAYER
    assert psm.playing.display_name == "Default Name"


async def test_set_state_calls_active_listener(psm, protocol_mock, listener):
    set_state = set_path(messages.create(pb.SET_STATE_MESSAGE))
    await protocol_mock.inject(set_state)

    assert listener.call_count == 1

    msg = messages.create(pb.SET_NOW_PLAYING_CLIENT_MESSAGE)
    client = msg.inner().client
    client.bundleIdentifier = CLIENT_ID_1
    await protocol_mock.inject(msg)

    assert listener.call_count == 2

    now_playing = set_path(messages.create(pb.SET_NOW_PLAYING_PLAYER_MESSAGE))
    await protocol_mock.inject(now_playing)

    assert listener.call_count == 3

    await protocol_mock.inject(set_state)

    assert listener.call_count == 4


async def test_content_item_update_calls_active_listener(psm, protocol_mock, listener):
    msg = set_path(messages.create(pb.SET_STATE_MESSAGE))
    await protocol_mock.inject(msg)

    assert listener.call_count == 1

    update_item = set_path(messages.create(pb.UPDATE_CONTENT_ITEM_MESSAGE))
    item = update_item.inner().contentItems.add()
    await protocol_mock.inject(update_item)

    assert listener.call_count == 2

    msg = messages.create(pb.SET_NOW_PLAYING_CLIENT_MESSAGE)
    client = msg.inner().client
    client.bundleIdentifier = CLIENT_ID_1
    await protocol_mock.inject(msg)

    assert listener.call_count == 3

    now_playing = set_path(messages.create(pb.SET_NOW_PLAYING_PLAYER_MESSAGE))
    await protocol_mock.inject(now_playing)

    assert listener.call_count == 4

    await protocol_mock.inject(update_item)

    assert listener.call_count == 5


async def test_update_client(psm, protocol_mock, listener):
    msg = messages.create(pb.SET_NOW_PLAYING_CLIENT_MESSAGE)
    client = msg.inner().client
    client.bundleIdentifier = CLIENT_ID_1
    await protocol_mock.inject(msg)

    assert listener.call_count == 1
    assert psm.client.display_name is None

    update = messages.create(pb.UPDATE_CLIENT_MESSAGE)
    client = update.inner().client
    client.bundleIdentifier = CLIENT_ID_1
    client.displayName = CLIENT_NAME_1
    await protocol_mock.inject(update)

    assert listener.call_count == 2
    assert psm.client.display_name == CLIENT_NAME_1


async def test_remove_active_client(psm, protocol_mock, listener):
    msg = set_path(messages.create(pb.SET_STATE_MESSAGE))
    await protocol_mock.inject(msg)

    msg = messages.create(pb.SET_NOW_PLAYING_CLIENT_MESSAGE)
    client = msg.inner().client
    client.bundleIdentifier = CLIENT_ID_1
    await protocol_mock.inject(msg)

    assert listener.call_count == 2
    assert psm.client.bundle_identifier == CLIENT_ID_1

    remove = messages.create(pb.REMOVE_CLIENT_MESSAGE)
    client = remove.inner().client
    client.bundleIdentifier = CLIENT_ID_1
    await protocol_mock.inject(remove)

    assert listener.call_count == 3
    assert psm.client is None


async def test_remove_not_active_client(psm, protocol_mock, listener):
    msg = set_path(messages.create(pb.SET_STATE_MESSAGE))
    await protocol_mock.inject(msg)

    msg = messages.create(pb.SET_NOW_PLAYING_CLIENT_MESSAGE)
    client = msg.inner().client
    client.bundleIdentifier = CLIENT_ID_1
    await protocol_mock.inject(msg)

    assert listener.call_count == 2
    assert psm.client.bundle_identifier == CLIENT_ID_1

    remove = messages.create(pb.REMOVE_CLIENT_MESSAGE)
    client = remove.inner().client
    client.bundleIdentifier = CLIENT_ID_2
    await protocol_mock.inject(remove)

    assert listener.call_count == 2
    assert psm.client.bundle_identifier == CLIENT_ID_1


async def test_remove_active_player(psm, protocol_mock, listener):
    msg = set_path(messages.create(pb.SET_STATE_MESSAGE))
    await protocol_mock.inject(msg)

    msg = messages.create(pb.SET_NOW_PLAYING_CLIENT_MESSAGE)
    client = msg.inner().client
    client.bundleIdentifier = CLIENT_ID_1
    await protocol_mock.inject(msg)

    msg = set_path(messages.create(pb.SET_NOW_PLAYING_PLAYER_MESSAGE))
    await protocol_mock.inject(msg)

    assert psm.playing.identifier == PLAYER_ID_1

    remove = set_path(messages.create(pb.REMOVE_PLAYER_MESSAGE))
    await protocol_mock.inject(remove)

    assert listener.call_count == 4
    assert not psm.playing.is_valid


async def test_remove_active_player_reverts_to_default(psm, protocol_mock, listener):
    msg = set_path(messages.create(pb.SET_STATE_MESSAGE), player_id=DEFAULT_PLAYER)
    await protocol_mock.inject(msg)

    msg = set_path(messages.create(pb.SET_NOW_PLAYING_PLAYER_MESSAGE))
    await protocol_mock.inject(msg)

    msg = messages.create(pb.SET_NOW_PLAYING_CLIENT_MESSAGE)
    client = msg.inner().client
    client.bundleIdentifier = CLIENT_ID_1
    await protocol_mock.inject(msg)

    assert listener.call_count == 2
    assert psm.playing.identifier == PLAYER_ID_1

    remove = set_path(messages.create(pb.REMOVE_PLAYER_MESSAGE))
    await protocol_mock.inject(remove)

    assert listener.call_count == 3
    assert psm.playing.identifier == DEFAULT_PLAYER


async def test_set_default_supported_commands(psm, protocol_mock, listener):
    msg = messages.create(pb.SET_DEFAULT_SUPPORTED_COMMANDS_MESSAGE)
    supported_commands = msg.inner().supportedCommands.supportedCommands
    command = supported_commands.add()
    command.command = pb.CommandInfo_pb2.Play
    msg.inner().playerPath.client.bundleIdentifier = CLIENT_ID_1
    await protocol_mock.inject(msg)

    msg = messages.create(pb.SET_NOW_PLAYING_CLIENT_MESSAGE)
    client = msg.inner().client
    client.bundleIdentifier = CLIENT_ID_1
    await protocol_mock.inject(msg)

    # Default commands are set on client, so any player belonging to that client
    # should have the supported command
    player_path = pb.PlayerPath()
    player_path.client.bundleIdentifier = CLIENT_ID_1
    player_path.player.identifier = PLAYER_ID_1
    player = psm.get_player(player_path)

    assert player.command_info(pb.CommandInfo_pb2.Play)
    assert listener.call_count == 2
