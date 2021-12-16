"""Unit tests for interface implementations in pyatv.protocols.mrp."""
import math

import pytest

from pyatv import exceptions
from pyatv.core.protocol import MessageDispatcher
from pyatv.protocols.mrp import MrpAudio, messages, protobuf

from tests.utils import until

DEVICE_UID = "F2204E63-BCAB-4941-80A0-06C46CB71391"


async def volume_controls_changed(protocol, device_uid, controls_available):
    message = messages.create(protobuf.VOLUME_CONTROL_CAPABILITIES_DID_CHANGE_MESSAGE)
    message.inner().outputDeviceUID = device_uid
    message.inner().capabilities.volumeControlAvailable = controls_available
    await protocol.inject(message)


# MrpAudio


@pytest.fixture(name="audio")
def audio_fixture(protocol_mock, mrp_state_dispatcher):
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


async def test_audio_set_volume(protocol_mock, audio):
    await volume_controls_changed(protocol_mock, DEVICE_UID, True)
    assert audio.is_available

    await audio.set_volume(0.0)

    assert len(protocol_mock.sent_messages) == 1

    message = protocol_mock.sent_messages.pop()
    assert message.type == protobuf.SET_VOLUME_MESSAGE
    assert message.inner().outputDeviceUID == DEVICE_UID
    assert math.isclose(message.inner().volume, 0.0, rel_tol=1e-02)


async def test_audio_set_volume_no_output_device(audio):
    with pytest.raises(exceptions.ProtocolError):
        await audio.set_volume(10)
