"""Unit tests for interface implementations in pyatv.protocols.mrp."""
import math

import pytest

from pyatv import exceptions
from pyatv.protocols.mrp import MrpAudio, messages, protobuf

DEVICE_UID = "F2204E63-BCAB-4941-80A0-06C46CB71391"


# This mock is _extremely_ basic, so needs to be adjusted heavily when adding
# new tests
class MrpProtocolMock:
    def __init__(self):
        self._listeners = {}
        self.sent_messages = []

    def add_listener(self, listener, message_type, data=None):
        self._listeners[message_type] = listener

    async def send(self, message):
        self.sent_messages.append(message)

    async def inject(self, message):
        await self._listeners[message.type](message, None)

    async def volume_controls_changed(self, device_uid, controls_available):
        message = messages.create(
            protobuf.VOLUME_CONTROL_CAPABILITIES_DID_CHANGE_MESSAGE
        )
        message.inner().outputDeviceUID = device_uid
        message.inner().capabilities.volumeControlAvailable = controls_available
        await self.inject(message)


@pytest.fixture(name="protocol")
def protocol_fixture(event_loop):
    yield MrpProtocolMock()


# MrpAudio


@pytest.fixture(name="audio")
def audio_fixture(protocol):
    yield MrpAudio(protocol)


async def test_audio_volume_control_availability(protocol, audio):
    assert not audio.is_available

    await protocol.volume_controls_changed(DEVICE_UID, True)
    assert audio.is_available

    await protocol.volume_controls_changed(DEVICE_UID, False)
    assert not audio.is_available


@pytest.mark.parametrize(
    "device_uid,controls_available,controls_expected",
    [
        (DEVICE_UID, True, True),
    ],
)
async def test_audio_volume_control_capabilities_changed(
    protocol, audio, device_uid, controls_available, controls_expected
):
    assert not audio.is_available
    await protocol.volume_controls_changed(device_uid, controls_available)
    assert audio.is_available == controls_expected


@pytest.mark.parametrize(
    "device_uid,volume,expected_volume",
    [
        ("foo", 0.2, 0.0),  # deviceUID mismatch => no update
        (DEVICE_UID, 0.2, 20.0),  # deviceUID matches => update
    ],
)
async def test_audio_volume_did_change(
    protocol, audio, device_uid, volume, expected_volume
):
    await protocol.volume_controls_changed(DEVICE_UID, True)

    assert math.isclose(audio.volume, 0.0)

    message = messages.create(protobuf.VOLUME_DID_CHANGE_MESSAGE)
    message.inner().outputDeviceUID = device_uid
    message.inner().volume = volume
    await protocol.inject(message)
    assert math.isclose(audio.volume, expected_volume)


async def test_audio_set_volume(protocol, audio):
    await protocol.volume_controls_changed(DEVICE_UID, True)

    await audio.set_volume(0.0)

    assert len(protocol.sent_messages) == 1

    message = protocol.sent_messages.pop()
    assert message.type == protobuf.SET_VOLUME_MESSAGE
    assert message.inner().outputDeviceUID == DEVICE_UID
    assert math.isclose(message.inner().volume, 0.0, rel_tol=1e-02)


async def test_audio_set_volume_no_output_device(audio):
    with pytest.raises(exceptions.ProtocolError):
        await audio.set_volume(10)
