"""Helper code for dealing with protobuf messages."""

import binascii

from pyatv import const
from pyatv.mrp import protobuf
from pyatv.mrp import tlv8


def create(message_type, priority=0, identifier=None):
    """Create a ProtocolMessage."""
    message = protobuf.ProtocolMessage()
    message.type = message_type
    message.priority = priority
    if identifier:
        message.identifier = identifier
    return message


def device_information(name, identifier):
    """Create a new DEVICE_INFO_MESSAGE."""
    # pylint: disable=no-member
    message = create(protobuf.DEVICE_INFO_MESSAGE)
    info = message.inner()
    info.allowsPairing = True
    info.applicationBundleIdentifier = 'com.apple.TVRemote'
    info.applicationBundleVersion = '344.28'
    info.lastSupportedMessageType = 77
    info.localizedModelName = 'iPhone'
    info.name = name
    info.protocolVersion = 1
    info.sharedQueueVersion = 2
    info.supportsACL = True
    info.supportsExtendedMotion = True
    info.supportsSharedQueue = True
    info.supportsSystemPairing = True
    info.systemBuildVersion = '17B111'
    info.systemMediaApplication = "com.apple.TVMusic"
    info.uniqueIdentifier = identifier
    info.deviceClass = 1
    info.logicalDeviceCount = 1
    return message


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
    crypto.pairingData = tlv8.write_tlv(pairing_data)

    # Hardcoded values for now, might have to be changed
    crypto.isRetrying = False
    crypto.isUsingSystemPairing = False
    crypto.state = 2 if is_pairing else 0
    return message


def client_updates_config(artwork=True, now_playing=False,
                          volume=False, keyboard=True):
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
    return message


def send_hid_event(use_page, usage, down):
    """Create a new SEND_HID_EVENT_MESSAGE."""
    message = create(protobuf.SEND_HID_EVENT_MESSAGE)
    event = message.inner()

    # TODO: This should be generated somehow. I guess it's mach AbsoluteTime
    # which is tricky to generate. The device does not seem to care much about
    # the value though, so hardcode something here.
    abstime = binascii.unhexlify(b'438922cf08020000')

    data = use_page.to_bytes(2, byteorder='big')
    data += usage.to_bytes(2, byteorder='big')
    data += (1 if down else 0).to_bytes(2, byteorder='big')

    # This is the format that the device expects. Some day I might take some
    # time to decode it for real, but this is fine for now.
    event.hidEventData = abstime + \
        binascii.unhexlify(b'00000000000000000100000000000000020' +
                           b'00000200000000300000001000000000000') + \
        data + \
        binascii.unhexlify(b'0000000000000001000000')

    return message


def command(cmd):
    """Playback command request."""
    message = create(protobuf.SEND_COMMAND_MESSAGE)
    send_command = message.inner()
    send_command.command = cmd
    return message


def repeat(mode):
    """Change repeat mode of current player."""
    message = command(protobuf.CommandInfo_pb2.ChangeRepeatMode)
    options = message.inner().options
    options.sendOptions = 0
    if mode == const.RepeatState.Track:
        options.repeatMode = protobuf.CommandInfo.One
    elif mode == const.RepeatState.All:
        options.repeatMode = protobuf.CommandInfo.All
    return message


def shuffle(state):
    """Change shuffle mode of current player."""
    message = command(protobuf.CommandInfo_pb2.ChangeShuffleMode)
    options = message.inner().options
    options.sendOptions = 0
    if state == const.ShuffleState.Off:
        options.shuffleMode = protobuf.CommandInfo.Off
    elif state == const.ShuffleState.Albums:
        options.shuffleMode = protobuf.CommandInfo.Albums
    else:
        options.shuffleMode = protobuf.CommandInfo.Songs
    return message


def seek_to_position(position):
    """Seek to an absolute position in stream."""
    message = command(protobuf.CommandInfo_pb2.SeekToPlaybackPosition)
    send_command = message.inner()
    send_command.options.playbackPosition = position
    return message
