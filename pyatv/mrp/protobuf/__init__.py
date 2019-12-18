"""Simplified extension handling for protobuf messages.

THIS CODE IS AUTO-GENERATED - DO NOT EDIT!!!
"""

from pyatv.mrp.protobuf.ProtocolMessage_pb2 import ProtocolMessage


from pyatv.mrp.protobuf import ClientUpdatesConfigMessage_pb2
from pyatv.mrp.protobuf import CryptoPairingMessage_pb2
from pyatv.mrp.protobuf import DeviceInfoMessage_pb2
from pyatv.mrp.protobuf import GetKeyboardSessionMessage_pb2
from pyatv.mrp.protobuf import KeyboardMessage_pb2
from pyatv.mrp.protobuf import NotificationMessage_pb2
from pyatv.mrp.protobuf import PlaybackQueueRequestMessage_pb2
from pyatv.mrp.protobuf import RegisterForGameControllerEventsMessage_pb2
from pyatv.mrp.protobuf import RegisterHIDDeviceMessage_pb2
from pyatv.mrp.protobuf import RegisterHIDDeviceResultMessage_pb2
from pyatv.mrp.protobuf import RegisterVoiceInputDeviceMessage_pb2
from pyatv.mrp.protobuf import RegisterVoiceInputDeviceResponseMessage_pb2
from pyatv.mrp.protobuf import SendCommandMessage_pb2
from pyatv.mrp.protobuf import SendCommandResultMessage_pb2
from pyatv.mrp.protobuf import SendHIDEventMessage_pb2
from pyatv.mrp.protobuf import SendPackedVirtualTouchEventMessage_pb2
from pyatv.mrp.protobuf import SetArtworkMessage_pb2
from pyatv.mrp.protobuf import SetConnectionStateMessage_pb2
from pyatv.mrp.protobuf import SetHiliteModeMessage_pb2
from pyatv.mrp.protobuf import SetNowPlayingClientMessage_pb2
from pyatv.mrp.protobuf import SetStateMessage_pb2
from pyatv.mrp.protobuf import TextInputMessage_pb2
from pyatv.mrp.protobuf import TransactionMessage_pb2
from pyatv.mrp.protobuf import UpdateClientMessage_pb2
from pyatv.mrp.protobuf import UpdateContentItemMessage_pb2
from pyatv.mrp.protobuf import VolumeControlAvailabilityMessage_pb2
from pyatv.mrp.protobuf import WakeDeviceMessage_pb2


from pyatv.mrp.protobuf.AudioFormatSettingsMessage_pb2 import AudioFormatSettings
from pyatv.mrp.protobuf.ClientUpdatesConfigMessage_pb2 import ClientUpdatesConfigMessage
from pyatv.mrp.protobuf.CommandInfo_pb2 import CommandInfo
from pyatv.mrp.protobuf.CommandOptions_pb2 import CommandOptions
from pyatv.mrp.protobuf.ContentItemMetadata_pb2 import ContentItemMetadata
from pyatv.mrp.protobuf.ContentItem_pb2 import ContentItem
from pyatv.mrp.protobuf.CryptoPairingMessage_pb2 import CryptoPairingMessage
from pyatv.mrp.protobuf.DeviceInfoMessage_pb2 import DeviceInfoMessage
from pyatv.mrp.protobuf.GetKeyboardSessionMessage_pb2 import GetKeyboardSessionMessage
from pyatv.mrp.protobuf.KeyboardMessage_pb2 import KeyboardMessage
from pyatv.mrp.protobuf.LanguageOption_pb2 import LanguageOption
from pyatv.mrp.protobuf.NotificationMessage_pb2 import NotificationMessage
from pyatv.mrp.protobuf.NowPlayingClient_pb2 import NowPlayingClient
from pyatv.mrp.protobuf.NowPlayingInfo_pb2 import NowPlayingInfo
from pyatv.mrp.protobuf.NowPlayingPlayer_pb2 import NowPlayingPlayer
from pyatv.mrp.protobuf.Origin_pb2 import Origin
from pyatv.mrp.protobuf.PlaybackQueueCapabilities_pb2 import PlaybackQueueCapabilities
from pyatv.mrp.protobuf.PlaybackQueueContext_pb2 import PlaybackQueueContext
from pyatv.mrp.protobuf.PlaybackQueueRequestMessage_pb2 import PlaybackQueueRequestMessage
from pyatv.mrp.protobuf.PlaybackQueue_pb2 import PlaybackQueue
from pyatv.mrp.protobuf.PlayerPath_pb2 import PlayerPath
from pyatv.mrp.protobuf.RegisterForGameControllerEventsMessage_pb2 import RegisterForGameControllerEventsMessage
from pyatv.mrp.protobuf.RegisterHIDDeviceMessage_pb2 import RegisterHIDDeviceMessage
from pyatv.mrp.protobuf.RegisterHIDDeviceResultMessage_pb2 import RegisterHIDDeviceResultMessage
from pyatv.mrp.protobuf.RegisterVoiceInputDeviceMessage_pb2 import RegisterVoiceInputDeviceMessage
from pyatv.mrp.protobuf.RegisterVoiceInputDeviceResponseMessage_pb2 import RegisterVoiceInputDeviceResponseMessage
from pyatv.mrp.protobuf.SendCommandMessage_pb2 import SendCommandMessage
from pyatv.mrp.protobuf.SendCommandResultMessage_pb2 import SendCommandResultMessage
from pyatv.mrp.protobuf.SendHIDEventMessage_pb2 import SendHIDEventMessage
from pyatv.mrp.protobuf.SendPackedVirtualTouchEventMessage_pb2 import SendPackedVirtualTouchEventMessage
from pyatv.mrp.protobuf.SetArtworkMessage_pb2 import SetArtworkMessage
from pyatv.mrp.protobuf.SetConnectionStateMessage_pb2 import SetConnectionStateMessage
from pyatv.mrp.protobuf.SetHiliteModeMessage_pb2 import SetHiliteModeMessage
from pyatv.mrp.protobuf.SetNowPlayingClientMessage_pb2 import SetNowPlayingClientMessage
from pyatv.mrp.protobuf.SetStateMessage_pb2 import SetStateMessage
from pyatv.mrp.protobuf.SupportedCommands_pb2 import SupportedCommands
from pyatv.mrp.protobuf.TextEditingAttributesMessage_pb2 import TextEditingAttributes
from pyatv.mrp.protobuf.TextInputMessage_pb2 import TextInputMessage
from pyatv.mrp.protobuf.TextInputTraitsMessage_pb2 import TextInputTraits
from pyatv.mrp.protobuf.TransactionKey_pb2 import TransactionKey
from pyatv.mrp.protobuf.TransactionMessage_pb2 import TransactionMessage
from pyatv.mrp.protobuf.TransactionPacket_pb2 import TransactionPacket
from pyatv.mrp.protobuf.TransactionPackets_pb2 import TransactionPackets
from pyatv.mrp.protobuf.UpdateClientMessage_pb2 import UpdateClientMessage
from pyatv.mrp.protobuf.UpdateContentItemMessage_pb2 import UpdateContentItemMessage
from pyatv.mrp.protobuf.VirtualTouchDeviceDescriptorMessage_pb2 import VirtualTouchDeviceDescriptor
from pyatv.mrp.protobuf.VoiceInputDeviceDescriptorMessage_pb2 import VoiceInputDeviceDescriptor
from pyatv.mrp.protobuf.VolumeControlAvailabilityMessage_pb2 import VolumeControlAvailabilityMessage
from pyatv.mrp.protobuf.WakeDeviceMessage_pb2 import WakeDeviceMessage


_EXTENSION_LOOKUP = {
    ProtocolMessage.CLIENT_UPDATES_CONFIG_MESSAGE: ClientUpdatesConfigMessage_pb2.clientUpdatesConfigMessage,
    ProtocolMessage.CRYPTO_PAIRING_MESSAGE: CryptoPairingMessage_pb2.cryptoPairingMessage,
    ProtocolMessage.DEVICE_INFO_MESSAGE: DeviceInfoMessage_pb2.deviceInfoMessage,
    ProtocolMessage.DEVICE_INFO_UPDATE_MESSAGE: DeviceInfoMessage_pb2.deviceInfoMessage,
    ProtocolMessage.GET_KEYBOARD_SESSION_MESSAGE: GetKeyboardSessionMessage_pb2.getKeyboardSessionMessage,
    ProtocolMessage.KEYBOARD_MESSAGE: KeyboardMessage_pb2.keyboardMessage,
    ProtocolMessage.NOTIFICATION_MESSAGE: NotificationMessage_pb2.notificationMessage,
    ProtocolMessage.PLAYBACK_QUEUE_REQUEST_MESSAGE: PlaybackQueueRequestMessage_pb2.playbackQueueRequestMessage,
    ProtocolMessage.REGISTER_FOR_GAME_CONTROLLER_EVENTS_MESSAGE: RegisterForGameControllerEventsMessage_pb2.registerForGameControllerEventsMessage,
    ProtocolMessage.REGISTER_HID_DEVICE_MESSAGE: RegisterHIDDeviceMessage_pb2.registerHIDDeviceMessage,
    ProtocolMessage.REGISTER_HID_DEVICE_RESULT_MESSAGE: RegisterHIDDeviceResultMessage_pb2.registerHIDDeviceResultMessage,
    ProtocolMessage.REGISTER_VOICE_INPUT_DEVICE_MESSAGE: RegisterVoiceInputDeviceMessage_pb2.registerVoiceInputDeviceMessage,
    ProtocolMessage.REGISTER_VOICE_INPUT_DEVICE_RESPONSE_MESSAGE: RegisterVoiceInputDeviceResponseMessage_pb2.registerVoiceInputDeviceResponseMessage,
    ProtocolMessage.SEND_COMMAND_MESSAGE: SendCommandMessage_pb2.sendCommandMessage,
    ProtocolMessage.SEND_COMMAND_RESULT_MESSAGE: SendCommandResultMessage_pb2.sendCommandResultMessage,
    ProtocolMessage.SEND_HID_EVENT_MESSAGE: SendHIDEventMessage_pb2.sendHIDEventMessage,
    ProtocolMessage.SEND_PACKED_VIRTUAL_TOUCH_EVENT_MESSAGE: SendPackedVirtualTouchEventMessage_pb2.sendPackedVirtualTouchEventMessage,
    ProtocolMessage.SET_ARTWORK_MESSAGE: SetArtworkMessage_pb2.setArtworkMessage,
    ProtocolMessage.SET_CONNECTION_STATE_MESSAGE: SetConnectionStateMessage_pb2.setConnectionStateMessage,
    ProtocolMessage.SET_HILITE_MODE_MESSAGE: SetHiliteModeMessage_pb2.setHiliteModeMessage,
    ProtocolMessage.SET_NOW_PLAYING_CLIENT_MESSAGE: SetNowPlayingClientMessage_pb2.setNowPlayingClientMessage,
    ProtocolMessage.SET_STATE_MESSAGE: SetStateMessage_pb2.setStateMessage,
    ProtocolMessage.TEXT_INPUT_MESSAGE: TextInputMessage_pb2.textInputMessage,
    ProtocolMessage.TRANSACTION_MESSAGE: TransactionMessage_pb2.transactionMessage,
    ProtocolMessage.UPDATE_CLIENT_MESSAGE: UpdateClientMessage_pb2.updateClientMessage,
    ProtocolMessage.UPDATE_CONTENT_ITEM_MESSAGE: UpdateContentItemMessage_pb2.updateContentItemMessage,
    ProtocolMessage.VOLUME_CONTROL_AVAILABILITY_MESSAGE: VolumeControlAvailabilityMessage_pb2.volumeControlAvailabilityMessage,
    ProtocolMessage.WAKE_DEVICE_MESSAGE: WakeDeviceMessage_pb2.wakeDeviceMessage,
}


CLIENT_UPDATES_CONFIG_MESSAGE = ProtocolMessage.CLIENT_UPDATES_CONFIG_MESSAGE
CRYPTO_PAIRING_MESSAGE = ProtocolMessage.CRYPTO_PAIRING_MESSAGE
DEVICE_INFO_MESSAGE = ProtocolMessage.DEVICE_INFO_MESSAGE
GET_KEYBOARD_SESSION_MESSAGE = ProtocolMessage.GET_KEYBOARD_SESSION_MESSAGE
KEYBOARD_MESSAGE = ProtocolMessage.KEYBOARD_MESSAGE
NOTIFICATION_MESSAGE = ProtocolMessage.NOTIFICATION_MESSAGE
PLAYBACK_QUEUE_REQUEST_MESSAGE = ProtocolMessage.PLAYBACK_QUEUE_REQUEST_MESSAGE
REGISTER_FOR_GAME_CONTROLLER_EVENTS_MESSAGE = ProtocolMessage.REGISTER_FOR_GAME_CONTROLLER_EVENTS_MESSAGE
REGISTER_HID_DEVICE_MESSAGE = ProtocolMessage.REGISTER_HID_DEVICE_MESSAGE
REGISTER_HID_DEVICE_RESULT_MESSAGE = ProtocolMessage.REGISTER_HID_DEVICE_RESULT_MESSAGE
REGISTER_VOICE_INPUT_DEVICE_MESSAGE = ProtocolMessage.REGISTER_VOICE_INPUT_DEVICE_MESSAGE
REGISTER_VOICE_INPUT_DEVICE_RESPONSE_MESSAGE = ProtocolMessage.REGISTER_VOICE_INPUT_DEVICE_RESPONSE_MESSAGE
SEND_COMMAND_MESSAGE = ProtocolMessage.SEND_COMMAND_MESSAGE
SEND_COMMAND_RESULT_MESSAGE = ProtocolMessage.SEND_COMMAND_RESULT_MESSAGE
SEND_HID_EVENT_MESSAGE = ProtocolMessage.SEND_HID_EVENT_MESSAGE
SEND_PACKED_VIRTUAL_TOUCH_EVENT_MESSAGE = ProtocolMessage.SEND_PACKED_VIRTUAL_TOUCH_EVENT_MESSAGE
SET_ARTWORK_MESSAGE = ProtocolMessage.SET_ARTWORK_MESSAGE
SET_CONNECTION_STATE_MESSAGE = ProtocolMessage.SET_CONNECTION_STATE_MESSAGE
SET_HILITE_MODE_MESSAGE = ProtocolMessage.SET_HILITE_MODE_MESSAGE
SET_NOW_PLAYING_CLIENT_MESSAGE = ProtocolMessage.SET_NOW_PLAYING_CLIENT_MESSAGE
SET_STATE_MESSAGE = ProtocolMessage.SET_STATE_MESSAGE
TEXT_INPUT_MESSAGE = ProtocolMessage.TEXT_INPUT_MESSAGE
TRANSACTION_MESSAGE = ProtocolMessage.TRANSACTION_MESSAGE
UPDATE_CLIENT_MESSAGE = ProtocolMessage.UPDATE_CLIENT_MESSAGE
UPDATE_CONTENT_ITEM_MESSAGE = ProtocolMessage.UPDATE_CONTENT_ITEM_MESSAGE
VOLUME_CONTROL_AVAILABILITY_MESSAGE = ProtocolMessage.VOLUME_CONTROL_AVAILABILITY_MESSAGE
WAKE_DEVICE_MESSAGE = ProtocolMessage.WAKE_DEVICE_MESSAGE


def _inner_message(self):
    extension = _EXTENSION_LOOKUP.get(self.type, None)
    if extension:
        return self.Extensions[extension]

    raise Exception('unknown type: ' + str(self.type))


ProtocolMessage.inner = _inner_message  # type: ignore

