"""Helper code for dealing with protobuf messages."""

from pyatv import const
from pyatv.mrp import protobuf
from pyatv.support import hap_tlv8


def create(message_type, error_code=0, identifier=None):
    """Create a ProtocolMessage."""
    message = protobuf.ProtocolMessage()
    message.type = message_type
    message.errorCode = error_code
    if identifier:
        message.identifier = identifier
    return message


def device_information(name, identifier, update=False):
    """Create a new DEVICE_INFO_MESSAGE."""
    msg_type = (
        protobuf.DEVICE_INFO_UPDATE_MESSAGE if update else protobuf.DEVICE_INFO_MESSAGE
    )
    message = create(msg_type)
    info = message.inner()
    info.allowsPairing = True
    info.applicationBundleIdentifier = "com.apple.TVRemote"
    info.applicationBundleVersion = "344.28"
    info.lastSupportedMessageType = 77
    info.localizedModelName = "iPhone"
    info.name = name
    info.protocolVersion = 1
    info.sharedQueueVersion = 2
    info.supportsACL = True
    info.supportsExtendedMotion = True
    info.supportsSharedQueue = True
    info.supportsSystemPairing = True
    info.systemBuildVersion = "17B111"
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


def client_updates_config(artwork=True, now_playing=False, volume=True, keyboard=True):
    """Create a new CLIENT_UPDATES_CONFIG_MESSAGE."""
    message = create(protobuf.CLIENT_UPDATES_CONFIG_MESSAGE)
    config = message.inner()
    config.artworkUpdates = artwork
    config.nowPlayingUpdates = now_playing
    config.volumeUpdates = volume
    config.keyboardUpdates = keyboard
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

def command(cmd, **kwargs):
    """Playback command request."""
    message = create(protobuf.SEND_COMMAND_MESSAGE)
    send_command = message.inner()
    send_command.command = cmd
    for key, value in kwargs.items():
        setattr(send_command.options, key, value)
    return message

def send_button(usage_page, usage, button_down):
    """Send button event."""
    message = create(protobuf.SEND_BUTTON_EVENT_MESSAGE)
    send_button = message.inner()
    send_button.usagePage = usage_page
    send_button.usage = usage
    send_button.buttonDown = button_down
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
