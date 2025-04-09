"""Unit tests for interface implementations in pyatv.protocols.mrp."""

import datetime
import math
from typing import Any, Dict
from unittest.mock import Mock, PropertyMock

import pytest

from pyatv import exceptions
from pyatv.core import UpdatedState
from pyatv.interface import ClientSessionManager, OutputDevice
from pyatv.protocols.mrp import MrpAudio, MrpMetadata, messages, player_state, protobuf
from pyatv.settings import InfoSettings

from tests.utils import faketime

DEVICE_NAME = "Apple TV"
DEVICE_UID = "F2204E63-BCAB-4941-80A0-06C46CB71391"

pytestmark = pytest.mark.asyncio


async def volume_controls_changed(protocol, device_uid, controls_available):
    message = messages.create(protobuf.VOLUME_CONTROL_CAPABILITIES_DID_CHANGE_MESSAGE)
    message.inner().outputDeviceUID = device_uid
    message.inner().capabilities.volumeControlAvailable = controls_available
    await protocol.inject(message)


async def grouped_devices_changed(protocol, is_leader, is_proxy, grouped_devices):
    message = messages.create(protobuf.DEVICE_INFO_UPDATE_MESSAGE)
    inner = message.inner()
    inner.name = DEVICE_NAME
    inner.uniqueIdentifier = DEVICE_UID
    inner.isGroupLeader = True
    inner.isGroupLeader = is_leader
    inner.isProxyGroupPlayer = is_proxy
    for device in grouped_devices:
        device_info = protobuf.DeviceInfoMessage()
        device_info.name = device.name
        device_info.deviceUID = device.identifier
        inner.groupedDevices.append(device_info)
    await protocol.inject(message)


# MrpAudio


@pytest.fixture(name="audio")
def audio_fixture(protocol_mock, mrp_state_dispatcher):
    info = InfoSettings()
    info.name = "test"

    device_info = messages.device_information(info, "id")
    device_info.inner().deviceUID = DEVICE_UID
    protocol_mock.device_info = device_info
    yield MrpAudio(protocol_mock, mrp_state_dispatcher)


async def test_audio_volume_control_availability(protocol_mock, audio):
    assert not audio.is_available

    await volume_controls_changed(protocol_mock, DEVICE_UID, True)
    assert audio.is_available

    await volume_controls_changed(protocol_mock, DEVICE_UID, False)
    assert not audio.is_available


@pytest.mark.parametrize(
    "device_uid,controls_available,controls_expected",
    [
        ("foo", True, False),
        (DEVICE_UID, True, True),
    ],
)
async def test_audio_volume_control_capabilities_changed(
    protocol_mock, audio, device_uid, controls_available, controls_expected
):
    assert not audio.is_available
    await volume_controls_changed(protocol_mock, device_uid, controls_available)
    assert audio.is_available == controls_expected


@pytest.mark.parametrize(
    "device_uid,volume,expected_volume",
    [
        ("foo", 0.2, 0.0),  # deviceUID mismatch => no update
        (DEVICE_UID, 0.2, 20.0),  # deviceUID matches => update
    ],
)
async def test_audio_volume_did_change(
    protocol_mock, audio, device_uid, volume, expected_volume
):
    await volume_controls_changed(protocol_mock, DEVICE_UID, True)
    assert audio.is_available

    assert math.isclose(audio.volume, 0.0)

    message = messages.create(protobuf.VOLUME_DID_CHANGE_MESSAGE)
    message.inner().outputDeviceUID = device_uid
    message.inner().volume = volume
    await protocol_mock.inject(message)

    assert math.isclose(audio.volume, expected_volume)


@pytest.mark.parametrize(
    "device_uid,volume,expect_called,expected_volume",
    [
        ("foo", 0.2, False, None),  # deviceUID mismatch => no update
        (DEVICE_UID, 0.2, True, 20.0),  # deviceUID matches => update
    ],
)
async def test_audio_volume_did_change_dispatches(
    protocol_mock,
    audio,
    mrp_state_dispatcher,
    device_uid,
    volume,
    expect_called,
    expected_volume,
):
    await volume_controls_changed(protocol_mock, DEVICE_UID, True)
    assert audio.is_available

    assert math.isclose(audio.volume, 0.0)

    callback = Mock()
    mrp_state_dispatcher.listen_to(UpdatedState.Volume, callback)

    message = messages.create(protobuf.VOLUME_DID_CHANGE_MESSAGE)
    message.inner().outputDeviceUID = device_uid
    message.inner().volume = volume
    await protocol_mock.inject(message)

    assert callback.called == expect_called
    if expected_volume is not None:
        message = callback.call_args.args[0]
        assert math.isclose(message.value, expected_volume)


async def test_audio_set_volume(protocol_mock, audio):
    await volume_controls_changed(protocol_mock, DEVICE_UID, True)
    assert audio.is_available

    await audio.set_volume(0.0)

    assert len(protocol_mock.sent_messages) == 1

    message = protocol_mock.sent_messages.pop()
    assert message.type == protobuf.SET_VOLUME_MESSAGE
    assert message.inner().outputDeviceUID == DEVICE_UID
    assert math.isclose(message.inner().volume, 0.0, rel_tol=1e-02)


async def test_audio_set_volume_no_output_device(protocol_mock, audio):
    protocol_mock.device_info = None
    with pytest.raises(exceptions.ProtocolError):
        await audio.set_volume(10)


@pytest.mark.parametrize(
    "is_leader,is_proxy,grouped_devices,expected_devices",
    [
        (True, False, [], [OutputDevice(DEVICE_NAME, DEVICE_UID)]),
        (
            True,
            False,
            [OutputDevice("HomePod", "FFFFFFFF-GGGG-HHHH-IIII-JJJJJJJJJJJJ")],
            [
                OutputDevice(DEVICE_NAME, DEVICE_UID),
                OutputDevice("HomePod", "FFFFFFFF-GGGG-HHHH-IIII-JJJJJJJJJJJJ"),
            ],
        ),
        (
            True,
            True,
            [OutputDevice("HomePod", "FFFFFFFF-GGGG-HHHH-IIII-JJJJJJJJJJJJ")],
            [OutputDevice("HomePod", "FFFFFFFF-GGGG-HHHH-IIII-JJJJJJJJJJJJ")],
        ),
        (False, False, [], []),
    ],
)
async def test_audio_update_output_devices(
    protocol_mock, audio, is_leader, is_proxy, grouped_devices, expected_devices
):
    await grouped_devices_changed(protocol_mock, is_leader, is_proxy, grouped_devices)
    assert audio.output_devices == expected_devices


@pytest.mark.parametrize(
    "is_leader,is_proxy,grouped_devices,expected_devices",
    [
        (True, False, [], [OutputDevice(DEVICE_NAME, DEVICE_UID)]),
        (
            True,
            False,
            [OutputDevice("HomePod", "FFFFFFFF-GGGG-HHHH-IIII-JJJJJJJJJJJJ")],
            [
                OutputDevice(DEVICE_NAME, DEVICE_UID),
                OutputDevice("HomePod", "FFFFFFFF-GGGG-HHHH-IIII-JJJJJJJJJJJJ"),
            ],
        ),
        (
            True,
            True,
            [OutputDevice("HomePod", "FFFFFFFF-GGGG-HHHH-IIII-JJJJJJJJJJJJ")],
            [OutputDevice("HomePod", "FFFFFFFF-GGGG-HHHH-IIII-JJJJJJJJJJJJ")],
        ),
        (False, False, [], []),
    ],
)
async def test_audio_update_output_devices_dispatches(
    protocol_mock,
    audio,
    mrp_state_dispatcher,
    is_leader,
    is_proxy,
    grouped_devices,
    expected_devices,
):
    callback = Mock()
    mrp_state_dispatcher.listen_to(UpdatedState.OutputDevices, callback)

    await grouped_devices_changed(protocol_mock, is_leader, is_proxy, grouped_devices)

    assert callback.called is True
    message = callback.call_args.args[0]
    assert message.value == expected_devices


async def test_audio_add_output_devices(protocol_mock, audio):
    # set event to finish test without timeout
    audio._output_devices_event.set()
    await audio.add_output_devices(
        "AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE", "FF:GG:HH:II:JJ:KK"
    )

    assert len(protocol_mock.sent_messages) == 1

    message = protocol_mock.sent_messages.pop()
    assert message.type == protobuf.MODIFY_OUTPUT_CONTEXT_REQUEST_MESSAGE
    assert message.inner().addingDevices == [
        "AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE",
        "FF:GG:HH:II:JJ:KK",
    ]
    assert message.inner().removingDevices == []
    assert message.inner().settingDevices == []
    assert message.inner().clusterAwareAddingDevices == [
        "AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE",
        "FF:GG:HH:II:JJ:KK",
    ]
    assert message.inner().clusterAwareRemovingDevices == []
    assert message.inner().clusterAwareSettingDevices == []


async def test_audio_remove_output_devices(protocol_mock, audio):
    # set event to finish test without timeout
    audio._output_devices_event.set()
    await audio.remove_output_devices(
        "AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE", "FF:GG:HH:II:JJ:KK"
    )

    assert len(protocol_mock.sent_messages) == 1

    message = protocol_mock.sent_messages.pop()
    assert message.type == protobuf.MODIFY_OUTPUT_CONTEXT_REQUEST_MESSAGE
    assert message.inner().addingDevices == []
    assert message.inner().removingDevices == [
        "AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE",
        "FF:GG:HH:II:JJ:KK",
    ]
    assert message.inner().settingDevices == []
    assert message.inner().clusterAwareAddingDevices == []
    assert message.inner().clusterAwareRemovingDevices == [
        "AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE",
        "FF:GG:HH:II:JJ:KK",
    ]
    assert message.inner().clusterAwareSettingDevices == []


async def test_audio_set_output_devices(protocol_mock, audio):
    # set event to finish test without timeout
    audio._output_devices_event.set()
    await audio.set_output_devices(
        "AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE", "FF:GG:HH:II:JJ:KK"
    )

    assert len(protocol_mock.sent_messages) == 1

    message = protocol_mock.sent_messages.pop()
    assert message.type == protobuf.MODIFY_OUTPUT_CONTEXT_REQUEST_MESSAGE
    assert message.inner().addingDevices == []
    assert message.inner().removingDevices == []
    assert message.inner().settingDevices == [
        "AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE",
        "FF:GG:HH:II:JJ:KK",
    ]
    assert message.inner().clusterAwareAddingDevices == []
    assert message.inner().clusterAwareRemovingDevices == []
    assert message.inner().clusterAwareSettingDevices == [
        "AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE",
        "FF:GG:HH:II:JJ:KK",
    ]


# MrpMetadata

ELAPSED_TIME = 2
ELAPSED_TIME_TIMESTAMP = 1
NOW_TIME = 10


@pytest.fixture(name="playing_metadata")
def playing_metadata_fixture() -> Dict[str, Any]:
    metadata = {}

    # Ok, so this is tricky to get right... We assume time starts at zero. As Apple
    # uses mach time (starts at 2001 instead of 1970), the elapsed time must be
    # converted to mach time. Any time can be used here, but one second has been
    # picked for simplicity. The elapsed time below is used to calculate position
    # in case media is playing, since "elapsedTime" only reflects time since playback
    # changed to "playing". So "elapsedTimeTimestamp" must be used as an additional
    # offset in case media is playing. By hardcoding to one second, we know that the
    # position essentially will be 1 + (time_now_mach - elapsedTimeTimestamp) IFF
    # something is playing. Otherwise it's just "elapsedTime".
    delta = datetime.datetime(1970, 1, 1) - datetime.datetime(2001, 1, 1)
    metadata["elapsedTimeTimestamp"] = (
        datetime.timedelta(seconds=ELAPSED_TIME_TIMESTAMP) + delta
    ).total_seconds()

    metadata["elapsedTime"] = ELAPSED_TIME

    # Start of in paused state
    metadata["playbackRate"] = 0.0
    player_state.playback_state = protobuf.PlaybackState.Paused

    yield metadata


@pytest.fixture(name="player_state")
def player_state_fixture(playing_metadata) -> Mock:
    playing_mock = Mock(name="playing_mock")
    playing_mock.metadata_field.side_effect = lambda field: playing_metadata.get(field)
    yield playing_mock


@pytest.fixture(name="metadata")
def metadata_fixture(
    protocol_mock, player_state, session_manager: ClientSessionManager
) -> MrpMetadata:
    psm_mock = Mock(name="metadata_mock")
    type(psm_mock).playing = PropertyMock(return_value=player_state)

    yield MrpMetadata(protocol_mock, psm_mock, "test", session_manager)


async def test_metadata_position_calculation(metadata, playing_metadata, player_state):
    # See playing_metadata fixture for timing details
    with faketime("pyatv", NOW_TIME):
        # Paused state => ELAPSED_TIME
        assert (await metadata.playing()).position == ELAPSED_TIME

        # Playing state => ELAPSED_TIME + time diff since "elapsedTimeTimestamp"
        player_state.playback_state = protobuf.PlaybackState.Playing
        playing_metadata["playbackRate"] = 1.0
        assert (await metadata.playing()).position == ELAPSED_TIME + (
            NOW_TIME - ELAPSED_TIME_TIMESTAMP
        )

        # Playing state but 0.0 playback rate => same as paused
        player_state.playback_state = protobuf.PlaybackState.Playing
        playing_metadata["playbackRate"] = 0.0
        assert (await metadata.playing()).position == ELAPSED_TIME
