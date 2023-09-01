"""Helper code for dealing with protobuf messages."""

import binascii
from typing import List
from uuid import uuid4

from pyatv import const
from pyatv.auth import hap_tlv8
from pyatv.protocols.mrp import protobuf
from pyatv.settings import InfoSettings


def create(message_type, error_code=0, identifier=None):
    """Create a ProtocolMessage."""
    message = protobuf.ProtocolMessage()
    message.type = message_type
    message.errorCode = error_code
    message.uniqueIdentifier = str(uuid4()).upper()
    if identifier:
        message.identifier = identifier
    return message


def device_information(info_settings: InfoSettings, identifier, update=False):
    """Create a new DEVICE_INFO_MESSAGE."""
    msg_type = (
        protobuf.DEVICE_INFO_UPDATE_MESSAGE if update else protobuf.DEVICE_INFO_MESSAGE
    )
    message = create(msg_type)
    info = message.inner()
    info.allowsPairing = True
    info.applicationBundleIdentifier = "com.apple.TVRemote"
    info.applicationBundleVersion = "344.28"
    info.lastSupportedMessageType = 108
    info.localizedModelName = "iPhone"
    info.name = info_settings.name
    info.protocolVersion = 1
    info.sharedQueueVersion = 2
    info.supportsACL = True
    info.supportsExtendedMotion = True
    info.supportsSharedQueue = True
    info.supportsSystemPairing = True
    info.systemBuildVersion = info_settings.os_build
    info.systemMediaApplication = "com.apple.TVMusic"
    info.uniqueIdentifier = identifier
    info.deviceClass = protobuf.DeviceClass.iPhone
    info.logicalDeviceCount = 1
    return message


def wake_device():
    """Create a new WAKE_DEVICE_MESSAGE."""
    return create(protobuf.ProtocolMessage.WAKE_DEVICE_MESSAGE)


def set_connection_state():
    """Create a new SET_CONNECTION_STATE."""
    message = create(protobuf.ProtocolMessage.SET_CONNECTION_STATE_MESSAGE)
    message.inner().state = protobuf.SetConnectionStateMessage.Connected
    return message


def get_keyboard_session():
    """Create a new GET_KEYBOARD_SESSION_MESSAGE."""
    return create(protobuf.ProtocolMessage.GET_KEYBOARD_SESSION_MESSAGE)


def crypto_pairing(pairing_data, is_pairing=False):
    """Create a new CRYPTO_PAIRING_MESSAGE."""
    message = create(protobuf.CRYPTO_PAIRING_MESSAGE)
    crypto = message.inner()
    crypto.status = 0
    crypto.pairingData = hap_tlv8.write_tlv(pairing_data)

    # Hardcoded values for now, might have to be changed
    crypto.isRetrying = False
    crypto.isUsingSystemPairing = False
    crypto.state = 2 if is_pairing else 0
    return message


def client_updates_config(
    artwork=True,
    now_playing=False,
    volume=True,
    keyboard=True,
    output_device_updates=True,
):
    """Create a new CLIENT_UPDATES_CONFIG_MESSAGE."""
    message = create(protobuf.CLIENT_UPDATES_CONFIG_MESSAGE)
    config = message.inner()
    config.artworkUpdates = artwork
    config.nowPlayingUpdates = now_playing
    config.volumeUpdates = volume
    config.keyboardUpdates = keyboard
    config.outputDeviceUpdates = output_device_updates
    return message


def playback_queue_request(location, width=-1, height=400):
    """Create a new PLAYBACK_QUEUE_REQUEST."""
    message = create(protobuf.PLAYBACK_QUEUE_REQUEST_MESSAGE)
    request = message.inner()
    request.location = location
    request.length = 1
    request.artworkWidth = width
    request.artworkHeight = height
    request.returnContentItemAssetsInUserCompletion = True
    return message


def send_hid_event(use_page, usage, down):
    """Create a new SEND_HID_EVENT_MESSAGE."""
    message = create(protobuf.SEND_HID_EVENT_MESSAGE)
    event = message.inner()

    # TODO: This should be generated somehow. I guess it's mach AbsoluteTime
    # which is tricky to generate. The device does not seem to care much about
    # the value though, so hardcode something here.
    abstime = binascii.unhexlify(b"438922cf08020000")

    data = use_page.to_bytes(2, byteorder="big")
    data += usage.to_bytes(2, byteorder="big")
    data += (1 if down else 0).to_bytes(2, byteorder="big")

    # This is the format that the device expects. Some day I might take some
    # time to decode it for real, but this is fine for now.
    event.hidEventData = (
        abstime
        + binascii.unhexlify(
            b"00000000000000000100000000000000020"
            + b"00000200000000300000001000000000000"
        )
        + data
        + binascii.unhexlify(b"0000000000000001000000")
    )

    return message


def send_button(usage_page, usage, button_down):
    """Create a new SEND_BUTTON_EVENT_MESSAGE.."""
    message = create(protobuf.SEND_BUTTON_EVENT_MESSAGE)
    inner = message.inner()
    inner.usagePage = usage_page
    inner.usage = usage
    inner.buttonDown = button_down
    return message


def command(cmd, **kwargs):
    """Playback command request."""
    message = create(protobuf.SEND_COMMAND_MESSAGE)
    send_command = message.inner()
    send_command.command = cmd
    for key, value in kwargs.items():
        setattr(send_command.options, key, value)
    return message


def command_result(identifier, send_error=protobuf.SendError.NoError):
    """Playback command request."""
    message = create(protobuf.SEND_COMMAND_RESULT_MESSAGE, identifier=identifier)
    inner = message.inner()
    inner.sendError = send_error
    inner.handlerReturnStatus = protobuf.HandlerReturnStatus.Success
    return message


def repeat(mode):
    """Change repeat mode of current player."""
    message = command(protobuf.CommandInfo_pb2.ChangeRepeatMode)
    options = message.inner().options
    options.sendOptions = 0
    if mode == const.RepeatState.Off:
        options.repeatMode = protobuf.RepeatMode.Off
    elif mode == const.RepeatState.Track:
        options.repeatMode = protobuf.RepeatMode.One
    else:
        options.repeatMode = protobuf.RepeatMode.All
    return message


def shuffle(state):
    """Change shuffle mode of current player."""
    message = command(protobuf.CommandInfo_pb2.ChangeShuffleMode)
    options = message.inner().options
    options.sendOptions = 0
    if state == const.ShuffleState.Off:
        options.shuffleMode = protobuf.ShuffleMode.Off
    elif state == const.ShuffleState.Albums:
        options.shuffleMode = protobuf.ShuffleMode.Albums
    else:
        options.shuffleMode = protobuf.ShuffleMode.Songs
    return message


def seek_to_position(position):
    """Seek to an absolute position in stream."""
    message = command(protobuf.CommandInfo_pb2.SeekToPlaybackPosition)
    send_command = message.inner()
    send_command.options.playbackPosition = position
    return message


def set_volume(device_uid: str, volume: float) -> protobuf.ProtocolMessage:
    """Change volume on a device."""
    message = create(protobuf.SET_VOLUME_MESSAGE)
    inner = message.inner()
    inner.outputDeviceUID = device_uid
    inner.volume = volume
    return message


def add_output_devices(*device_uids: List[str]) -> protobuf.ProtocolMessage:
    """Add AirPlay devices to the speaker group."""
    message = create(protobuf.MODIFY_OUTPUT_CONTEXT_REQUEST_MESSAGE)
    inner = message.inner()
    inner.type = protobuf.ModifyOutputContextRequestType.SharedAudioPresentation
    for device_uid in device_uids:
        inner.addingDevices.append(device_uid)
        inner.clusterAwareAddingDevices.append(device_uid)
    return message


def remove_output_devices(*device_uids: List[str]) -> protobuf.ProtocolMessage:
    """Remove AirPlay devices from the speaker group."""
    message = create(protobuf.MODIFY_OUTPUT_CONTEXT_REQUEST_MESSAGE)
    inner = message.inner()
    inner.type = protobuf.ModifyOutputContextRequestType.SharedAudioPresentation
    for device_uid in device_uids:
        inner.removingDevices.append(device_uid)
        inner.clusterAwareRemovingDevices.append(device_uid)
    return message


def set_output_devices(*device_uids: List[str]) -> protobuf.ProtocolMessage:
    """Set AirPlay devices as the speaker group."""
    message = create(protobuf.MODIFY_OUTPUT_CONTEXT_REQUEST_MESSAGE)
    inner = message.inner()
    inner.type = protobuf.ModifyOutputContextRequestType.SharedAudioPresentation
    for device_uid in device_uids:
        inner.settingDevices.append(device_uid)
        inner.clusterAwareSettingDevices.append(device_uid)
    return message
