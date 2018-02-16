"""Helper code for dealing with protobuf messages."""

import binascii

from pyatv.mrp import protobuf
from pyatv.mrp import tlv8


def create(message_type, priority=0):
    """Create a ProtocolMessage."""
    message = protobuf.ProtocolMessage()
    message.type = message_type
    message.priority = priority
    return message


# TODO: default information here for the moment
def device_information(name, identifier):
    """Create a new DEVICE_INFO_MESSAGE."""
    # pylint: disable=no-member
    message = create(protobuf.DEVICE_INFO_MESSAGE)
    info = message.inner()
    info.uniqueIdentifier = identifier
    info.name = name
    info.localizedModelName = 'iPhone'
    info.systemBuildVersion = '14G60'
    info.applicationBundleIdentifier = 'com.apple.TVRemote'
    info.applicationBundleVersion = '273.12'
    info.protocolVersion = 1
    return message


def set_connection_state():
    """Create a new SET_CONNECTION_STATE_MESSAGE."""
    message = create(protobuf.SET_CONNECTION_STATE_MESSAGE)
    connection = message.inner()
    connection.state = protobuf.SetConnectionStateMessage.Connected
    return message


def crypto_pairing(pairing_data):
    """Create a new CRYPTO_PAIRING_MESSAGE."""
    message = create(protobuf.CRYPTO_PAIRING_MESSAGE)
    crypto = message.inner()
    crypto.status = 0
    crypto.pairingData = tlv8.write_tlv(pairing_data)
    return message


def client_updates_config(artwork=True, now_playing=True,
                          volume=True, keyboard=True):
    """Create a new CLIENT_UPDATES_CONFIG_MESSAGE."""
    message = create(protobuf.CLIENT_UPDATES_CONFIG_MESSAGE)
    config = message.inner()
    config.artworkUpdates = artwork
    config.nowPlayingUpdates = now_playing
    config.volumeUpdates = volume
    config.keyboardUpdates = keyboard
    return message


def wake_device():
    """Create a new WAKE_DEVICE_MESSAGE."""
    return create(protobuf.WAKE_DEVICE_MESSAGE)


def register_hid_device(screen_width, screen_height,
                        absolute=False, integrated_display=False):
    """Create a new REGISTER_HID_DEVICE_MESSAGE."""
    message = create(protobuf.REGISTER_HID_DEVICE_MESSAGE)
    descriptor = message.inner().deviceDescriptor
    descriptor.absolute = 1 if absolute else 0
    descriptor.integratedDisplay = 1 if integrated_display else 0
    descriptor.screenSizeWidth = screen_width
    descriptor.screenSizeHeight = screen_height
    return message


def send_packed_virtual_touch_event(xpos, ypos, phase, device_id, finger):
    """Create a new WAKE_DEVICE_MESSAGE."""
    message = create(protobuf.SEND_PACKED_VIRTUAL_TOUCH_EVENT_MESSAGE)
    event = message.inner()

    # The packed version of VirtualTouchEvent contains X, Y, phase, deviceID
    # and finger stored as a byte array. Each value is written as 16bit little
    # endian integers.
    event.data = xpos.to_bytes(2, byteorder='little')
    event.data += ypos.to_bytes(2, byteorder='little')
    event.data += phase.to_bytes(2, byteorder='little')
    event.data += device_id.to_bytes(2, byteorder='little')
    event.data += finger.to_bytes(2, byteorder='little')

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
