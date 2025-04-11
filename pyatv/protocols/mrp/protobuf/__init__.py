"""Simplified extension handling for protobuf messages.

THIS CODE IS AUTO-GENERATED - DO NOT EDIT!!!
"""

from .ProtocolMessage_pb2 import ProtocolMessage


from . import AudioFadeMessage_pb2
from . import AudioFadeResponseMessage_pb2
from . import ClientUpdatesConfigMessage_pb2
from . import ConfigureConnectionMessage_pb2
from . import CryptoPairingMessage_pb2
from . import DeviceInfoMessage_pb2
from . import GenericMessage_pb2
from . import GetKeyboardSessionMessage_pb2
from . import GetRemoteTextInputSessionMessage_pb2
from . import GetVolumeMessage_pb2
from . import GetVolumeResultMessage_pb2
from . import KeyboardMessage_pb2
from . import ModifyOutputContextRequestMessage_pb2
from . import NotificationMessage_pb2
from . import OriginClientPropertiesMessage_pb2
from . import PlaybackQueueRequestMessage_pb2
from . import PlayerClientPropertiesMessage_pb2
from . import RegisterForGameControllerEventsMessage_pb2
from . import RegisterHIDDeviceMessage_pb2
from . import RegisterHIDDeviceResultMessage_pb2
from . import RegisterVoiceInputDeviceMessage_pb2
from . import RegisterVoiceInputDeviceResponseMessage_pb2
from . import RemoteTextInputMessage_pb2
from . import RemoveClientMessage_pb2
from . import RemoveEndpointsMessage_pb2
from . import RemoveOutputDevicesMessage_pb2
from . import RemovePlayerMessage_pb2
from . import SendButtonEventMessage_pb2
from . import SendCommandMessage_pb2
from . import SendCommandResultMessage_pb2
from . import SendHIDEventMessage_pb2
from . import SendPackedVirtualTouchEventMessage_pb2
from . import SendVoiceInputMessage_pb2
from . import SetArtworkMessage_pb2
from . import SetConnectionStateMessage_pb2
from . import SetDefaultSupportedCommandsMessage_pb2
from . import SetDiscoveryModeMessage_pb2
from . import SetHiliteModeMessage_pb2
from . import SetNowPlayingClientMessage_pb2
from . import SetNowPlayingPlayerMessage_pb2
from . import SetRecordingStateMessage_pb2
from . import SetStateMessage_pb2
from . import SetVolumeMessage_pb2
from . import TextInputMessage_pb2
from . import TransactionMessage_pb2
from . import UpdateClientMessage_pb2
from . import UpdateContentItemArtworkMessage_pb2
from . import UpdateContentItemMessage_pb2
from . import UpdateEndPointsMessage_pb2
from . import UpdateOutputDeviceMessage_pb2
from . import VolumeControlAvailabilityMessage_pb2
from . import VolumeControlCapabilitiesDidChangeMessage_pb2
from . import VolumeDidChangeMessage_pb2
from . import WakeDeviceMessage_pb2


from .AudioFadeMessage_pb2 import AudioFadeMessage
from .AudioFadeResponseMessage_pb2 import AudioFadeResponseMessage
from .AudioFormatSettingsMessage_pb2 import AudioFormatSettings
from .ClientUpdatesConfigMessage_pb2 import ClientUpdatesConfigMessage
from .CommandInfo_pb2 import CommandInfo
from .CommandInfo_pb2 import DisableReason
from .CommandInfo_pb2 import PreloadedPlaybackSessionInfo
from .CommandInfo_pb2 import QueueEndAction
from .CommandOptions_pb2 import CommandOptions
from .Common_pb2 import DeviceClass
from .Common_pb2 import DeviceSubType
from .Common_pb2 import DeviceType
from .Common_pb2 import PlaybackState
from .Common_pb2 import RepeatMode
from .Common_pb2 import ShuffleMode
from .ConfigureConnectionMessage_pb2 import ConfigureConnectionMessage
from .ContentItemMetadata_pb2 import ActiveFormatJustification
from .ContentItemMetadata_pb2 import AlbumTraits
from .ContentItemMetadata_pb2 import AudioFormat
from .ContentItemMetadata_pb2 import AudioRoute
from .ContentItemMetadata_pb2 import AudioRouteType
from .ContentItemMetadata_pb2 import AudioTier
from .ContentItemMetadata_pb2 import ContentItemMetadata
from .ContentItemMetadata_pb2 import FormatTier
from .ContentItemMetadata_pb2 import PlaylistTraits
from .ContentItemMetadata_pb2 import SongTraits
from .ContentItem_pb2 import ContentItem
from .ContentItem_pb2 import LanguageOptionGroup
from .CryptoPairingMessage_pb2 import CryptoPairingMessage
from .DeviceInfoMessage_pb2 import DeviceInfoMessage
from .DeviceInfoMessage_pb2 import PreferredEncoding
from .GenericMessage_pb2 import GenericMessage
from .GetKeyboardSessionMessage_pb2 import GetKeyboardSessionMessage
from .GetRemoteTextInputSessionMessage_pb2 import GetRemoteTextInputSessionMessage
from .GetVolumeMessage_pb2 import GetVolumeMessage
from .GetVolumeResultMessage_pb2 import GetVolumeResultMessage
from .KeyboardMessage_pb2 import AutocapitalizationType
from .KeyboardMessage_pb2 import KeyboardMessage
from .KeyboardMessage_pb2 import KeyboardState
from .KeyboardMessage_pb2 import KeyboardType
from .KeyboardMessage_pb2 import ReturnKeyType
from .KeyboardMessage_pb2 import TextEditingAttributes
from .KeyboardMessage_pb2 import TextInputTraits
from .LanguageOption_pb2 import LanguageOption
from .ModifyOutputContextRequestMessage_pb2 import ModifyOutputContextRequestMessage
from .ModifyOutputContextRequestMessage_pb2 import ModifyOutputContextRequestType
from .NotificationMessage_pb2 import NotificationMessage
from .NowPlayingClient_pb2 import NowPlayingClient
from .NowPlayingInfo_pb2 import NowPlayingInfo
from .NowPlayingPlayer_pb2 import NowPlayingPlayer
from .OriginClientPropertiesMessage_pb2 import OriginClientPropertiesMessage
from .Origin_pb2 import Origin
from .PlaybackQueueCapabilities_pb2 import PlaybackQueueCapabilities
from .PlaybackQueueContext_pb2 import PlaybackQueueContext
from .PlaybackQueueRequestMessage_pb2 import PlaybackQueueRequestMessage
from .PlaybackQueue_pb2 import PlaybackQueue
from .PlayerClientPropertiesMessage_pb2 import PlayerClientPropertiesMessage
from .PlayerPath_pb2 import PlayerPath
from .RegisterForGameControllerEventsMessage_pb2 import RegisterForGameControllerEventsMessage
from .RegisterHIDDeviceMessage_pb2 import RegisterHIDDeviceMessage
from .RegisterHIDDeviceResultMessage_pb2 import RegisterHIDDeviceResultMessage
from .RegisterVoiceInputDeviceMessage_pb2 import RegisterVoiceInputDeviceMessage
from .RegisterVoiceInputDeviceResponseMessage_pb2 import RegisterVoiceInputDeviceResponseMessage
from .RemoteTextInputMessage_pb2 import RemoteTextInputMessage
from .RemoveClientMessage_pb2 import RemoveClientMessage
from .RemoveEndpointsMessage_pb2 import RemoveEndpointsMessage
from .RemoveOutputDevicesMessage_pb2 import RemoveOutputDevicesMessage
from .RemovePlayerMessage_pb2 import RemovePlayerMessage
from .SendButtonEventMessage_pb2 import SendButtonEventMessage
from .SendCommandMessage_pb2 import SendCommandMessage
from .SendCommandResultMessage_pb2 import HandlerReturnStatus
from .SendCommandResultMessage_pb2 import SendCommandResult
from .SendCommandResultMessage_pb2 import SendCommandResultMessage
from .SendCommandResultMessage_pb2 import SendCommandResultStatus
from .SendCommandResultMessage_pb2 import SendCommandResultType
from .SendCommandResultMessage_pb2 import SendCommandStatusCode
from .SendCommandResultMessage_pb2 import SendError
from .SendHIDEventMessage_pb2 import SendHIDEventMessage
from .SendPackedVirtualTouchEventMessage_pb2 import SendPackedVirtualTouchEventMessage
from .SendVoiceInputMessage_pb2 import AudioBuffer
from .SendVoiceInputMessage_pb2 import AudioDataBlock
from .SendVoiceInputMessage_pb2 import AudioStreamPacketDescription
from .SendVoiceInputMessage_pb2 import AudioTime
from .SendVoiceInputMessage_pb2 import SendVoiceInputMessage
from .SetArtworkMessage_pb2 import SetArtworkMessage
from .SetConnectionStateMessage_pb2 import SetConnectionStateMessage
from .SetDefaultSupportedCommandsMessage_pb2 import SetDefaultSupportedCommandsMessage
from .SetDiscoveryModeMessage_pb2 import SetDiscoveryModeMessage
from .SetHiliteModeMessage_pb2 import SetHiliteModeMessage
from .SetNowPlayingClientMessage_pb2 import SetNowPlayingClientMessage
from .SetNowPlayingPlayerMessage_pb2 import SetNowPlayingPlayerMessage
from .SetRecordingStateMessage_pb2 import SetRecordingStateMessage
from .SetStateMessage_pb2 import SetStateMessage
from .SetVolumeMessage_pb2 import SetVolumeMessage
from .SupportedCommands_pb2 import SupportedCommands
from .TextInputMessage_pb2 import ActionType
from .TextInputMessage_pb2 import TextInputMessage
from .TransactionKey_pb2 import TransactionKey
from .TransactionMessage_pb2 import TransactionMessage
from .TransactionPacket_pb2 import TransactionPacket
from .TransactionPackets_pb2 import TransactionPackets
from .UpdateClientMessage_pb2 import UpdateClientMessage
from .UpdateContentItemArtworkMessage_pb2 import UpdateContentItemArtworkMessage
from .UpdateContentItemMessage_pb2 import UpdateContentItemMessage
from .UpdateEndPointsMessage_pb2 import AVEndpointDescriptor
from .UpdateEndPointsMessage_pb2 import UpdateEndPointsMessage
from .UpdateOutputDeviceMessage_pb2 import AVOutputDeviceDescriptor
from .UpdateOutputDeviceMessage_pb2 import AVOutputDeviceSourceInfo
from .UpdateOutputDeviceMessage_pb2 import UpdateOutputDeviceMessage
from .UpdatePlayerPath_pb2 import UpdatePlayerMessage
from .VirtualTouchDeviceDescriptorMessage_pb2 import VirtualTouchDeviceDescriptor
from .VoiceInputDeviceDescriptorMessage_pb2 import VoiceInputDeviceDescriptor
from .VolumeControlAvailabilityMessage_pb2 import VolumeCapabilities
from .VolumeControlAvailabilityMessage_pb2 import VolumeControlAvailabilityMessage
from .VolumeControlCapabilitiesDidChangeMessage_pb2 import VolumeControlCapabilitiesDidChangeMessage
from .VolumeDidChangeMessage_pb2 import VolumeDidChangeMessage
from .WakeDeviceMessage_pb2 import WakeDeviceMessage


_EXTENSION_LOOKUP = {
    ProtocolMessage.AUDIO_FADE_MESSAGE: AudioFadeMessage_pb2.audioFadeMessage,
    ProtocolMessage.AUDIO_FADE_RESPONSE_MESSAGE: AudioFadeResponseMessage_pb2.audioFadeResponseMessage,
    ProtocolMessage.CLIENT_UPDATES_CONFIG_MESSAGE: ClientUpdatesConfigMessage_pb2.clientUpdatesConfigMessage,
    ProtocolMessage.CONFIGURE_CONNECTION_MESSAGE: ConfigureConnectionMessage_pb2.configureConnectionMessage,
    ProtocolMessage.CRYPTO_PAIRING_MESSAGE: CryptoPairingMessage_pb2.cryptoPairingMessage,
    ProtocolMessage.DEVICE_INFO_MESSAGE: DeviceInfoMessage_pb2.deviceInfoMessage,
    ProtocolMessage.DEVICE_INFO_UPDATE_MESSAGE: DeviceInfoMessage_pb2.deviceInfoMessage,
    ProtocolMessage.GENERIC_MESSAGE: GenericMessage_pb2.genericMessage,
    ProtocolMessage.GET_KEYBOARD_SESSION_MESSAGE: GetKeyboardSessionMessage_pb2.getKeyboardSessionMessage,
    ProtocolMessage.GET_REMOTE_TEXT_INPUT_SESSION_MESSAGE: GetRemoteTextInputSessionMessage_pb2.getRemoteTextInputSessionMessage,
    ProtocolMessage.GET_VOLUME_MESSAGE: GetVolumeMessage_pb2.getVolumeMessage,
    ProtocolMessage.GET_VOLUME_RESULT_MESSAGE: GetVolumeResultMessage_pb2.getVolumeResultMessage,
    ProtocolMessage.KEYBOARD_MESSAGE: KeyboardMessage_pb2.keyboardMessage,
    ProtocolMessage.MODIFY_OUTPUT_CONTEXT_REQUEST_MESSAGE: ModifyOutputContextRequestMessage_pb2.modifyOutputContextRequestMessage,
    ProtocolMessage.NOTIFICATION_MESSAGE: NotificationMessage_pb2.notificationMessage,
    ProtocolMessage.ORIGIN_CLIENT_PROPERTIES_MESSAGE: OriginClientPropertiesMessage_pb2.originClientPropertiesMessage,
    ProtocolMessage.PLAYBACK_QUEUE_REQUEST_MESSAGE: PlaybackQueueRequestMessage_pb2.playbackQueueRequestMessage,
    ProtocolMessage.PLAYER_CLIENT_PROPERTIES_MESSAGE: PlayerClientPropertiesMessage_pb2.playerClientPropertiesMessage,
    ProtocolMessage.REGISTER_FOR_GAME_CONTROLLER_EVENTS_MESSAGE: RegisterForGameControllerEventsMessage_pb2.registerForGameControllerEventsMessage,
    ProtocolMessage.REGISTER_HID_DEVICE_MESSAGE: RegisterHIDDeviceMessage_pb2.registerHIDDeviceMessage,
    ProtocolMessage.REGISTER_HID_DEVICE_RESULT_MESSAGE: RegisterHIDDeviceResultMessage_pb2.registerHIDDeviceResultMessage,
    ProtocolMessage.REGISTER_VOICE_INPUT_DEVICE_MESSAGE: RegisterVoiceInputDeviceMessage_pb2.registerVoiceInputDeviceMessage,
    ProtocolMessage.REGISTER_VOICE_INPUT_DEVICE_RESPONSE_MESSAGE: RegisterVoiceInputDeviceResponseMessage_pb2.registerVoiceInputDeviceResponseMessage,
    ProtocolMessage.REMOTE_TEXT_INPUT_MESSAGE: RemoteTextInputMessage_pb2.remoteTextInputMessage,
    ProtocolMessage.REMOVE_CLIENT_MESSAGE: RemoveClientMessage_pb2.removeClientMessage,
    ProtocolMessage.REMOVE_ENDPOINTS_MESSAGE: RemoveEndpointsMessage_pb2.removeEndpointsMessage,
    ProtocolMessage.REMOVE_OUTPUT_DEVICES_MESSAGE: RemoveOutputDevicesMessage_pb2.removeOutputDevicesMessage,
    ProtocolMessage.REMOVE_PLAYER_MESSAGE: RemovePlayerMessage_pb2.removePlayerMessage,
    ProtocolMessage.SEND_BUTTON_EVENT_MESSAGE: SendButtonEventMessage_pb2.sendButtonEventMessage,
    ProtocolMessage.SEND_COMMAND_MESSAGE: SendCommandMessage_pb2.sendCommandMessage,
    ProtocolMessage.SEND_COMMAND_RESULT_MESSAGE: SendCommandResultMessage_pb2.sendCommandResultMessage,
    ProtocolMessage.SEND_HID_EVENT_MESSAGE: SendHIDEventMessage_pb2.sendHIDEventMessage,
    ProtocolMessage.SEND_PACKED_VIRTUAL_TOUCH_EVENT_MESSAGE: SendPackedVirtualTouchEventMessage_pb2.sendPackedVirtualTouchEventMessage,
    ProtocolMessage.SEND_VOICE_INPUT_MESSAGE: SendVoiceInputMessage_pb2.sendVoiceInputMessage,
    ProtocolMessage.SET_ARTWORK_MESSAGE: SetArtworkMessage_pb2.setArtworkMessage,
    ProtocolMessage.SET_CONNECTION_STATE_MESSAGE: SetConnectionStateMessage_pb2.setConnectionStateMessage,
    ProtocolMessage.SET_DEFAULT_SUPPORTED_COMMANDS_MESSAGE: SetDefaultSupportedCommandsMessage_pb2.setDefaultSupportedCommandsMessage,
    ProtocolMessage.SET_DISCOVERY_MODE_MESSAGE: SetDiscoveryModeMessage_pb2.setDiscoveryModeMessage,
    ProtocolMessage.SET_HILITE_MODE_MESSAGE: SetHiliteModeMessage_pb2.setHiliteModeMessage,
    ProtocolMessage.SET_NOW_PLAYING_CLIENT_MESSAGE: SetNowPlayingClientMessage_pb2.setNowPlayingClientMessage,
    ProtocolMessage.SET_NOW_PLAYING_PLAYER_MESSAGE: SetNowPlayingPlayerMessage_pb2.setNowPlayingPlayerMessage,
    ProtocolMessage.SET_RECORDING_STATE_MESSAGE: SetRecordingStateMessage_pb2.setRecordingStateMessage,
    ProtocolMessage.SET_STATE_MESSAGE: SetStateMessage_pb2.setStateMessage,
    ProtocolMessage.SET_VOLUME_MESSAGE: SetVolumeMessage_pb2.setVolumeMessage,
    ProtocolMessage.TEXT_INPUT_MESSAGE: TextInputMessage_pb2.textInputMessage,
    ProtocolMessage.TRANSACTION_MESSAGE: TransactionMessage_pb2.transactionMessage,
    ProtocolMessage.UPDATE_CLIENT_MESSAGE: UpdateClientMessage_pb2.updateClientMessage,
    ProtocolMessage.UPDATE_CONTENT_ITEM_ARTWORK_MESSAGE: UpdateContentItemArtworkMessage_pb2.updateContentItemArtworkMessage,
    ProtocolMessage.UPDATE_CONTENT_ITEM_MESSAGE: UpdateContentItemMessage_pb2.updateContentItemMessage,
    ProtocolMessage.UPDATE_END_POINTS_MESSAGE: UpdateEndPointsMessage_pb2.updateEndPointsMessage,
    ProtocolMessage.UPDATE_OUTPUT_DEVICE_MESSAGE: UpdateOutputDeviceMessage_pb2.updateOutputDeviceMessage,
    ProtocolMessage.VOLUME_CONTROL_AVAILABILITY_MESSAGE: VolumeControlAvailabilityMessage_pb2.volumeControlAvailabilityMessage,
    ProtocolMessage.VOLUME_CONTROL_CAPABILITIES_DID_CHANGE_MESSAGE: VolumeControlCapabilitiesDidChangeMessage_pb2.volumeControlCapabilitiesDidChangeMessage,
    ProtocolMessage.VOLUME_DID_CHANGE_MESSAGE: VolumeDidChangeMessage_pb2.volumeDidChangeMessage,
    ProtocolMessage.WAKE_DEVICE_MESSAGE: WakeDeviceMessage_pb2.wakeDeviceMessage,
}


AUDIO_FADE_MESSAGE = ProtocolMessage.AUDIO_FADE_MESSAGE
AUDIO_FADE_RESPONSE_MESSAGE = ProtocolMessage.AUDIO_FADE_RESPONSE_MESSAGE
CLIENT_UPDATES_CONFIG_MESSAGE = ProtocolMessage.CLIENT_UPDATES_CONFIG_MESSAGE
CONFIGURE_CONNECTION_MESSAGE = ProtocolMessage.CONFIGURE_CONNECTION_MESSAGE
CRYPTO_PAIRING_MESSAGE = ProtocolMessage.CRYPTO_PAIRING_MESSAGE
DEVICE_INFO_MESSAGE = ProtocolMessage.DEVICE_INFO_MESSAGE
DEVICE_INFO_UPDATE_MESSAGE = ProtocolMessage.DEVICE_INFO_UPDATE_MESSAGE
GENERIC_MESSAGE = ProtocolMessage.GENERIC_MESSAGE
GET_KEYBOARD_SESSION_MESSAGE = ProtocolMessage.GET_KEYBOARD_SESSION_MESSAGE
GET_REMOTE_TEXT_INPUT_SESSION_MESSAGE = ProtocolMessage.GET_REMOTE_TEXT_INPUT_SESSION_MESSAGE
GET_VOLUME_MESSAGE = ProtocolMessage.GET_VOLUME_MESSAGE
GET_VOLUME_RESULT_MESSAGE = ProtocolMessage.GET_VOLUME_RESULT_MESSAGE
KEYBOARD_MESSAGE = ProtocolMessage.KEYBOARD_MESSAGE
MODIFY_OUTPUT_CONTEXT_REQUEST_MESSAGE = ProtocolMessage.MODIFY_OUTPUT_CONTEXT_REQUEST_MESSAGE
NOTIFICATION_MESSAGE = ProtocolMessage.NOTIFICATION_MESSAGE
ORIGIN_CLIENT_PROPERTIES_MESSAGE = ProtocolMessage.ORIGIN_CLIENT_PROPERTIES_MESSAGE
PLAYBACK_QUEUE_REQUEST_MESSAGE = ProtocolMessage.PLAYBACK_QUEUE_REQUEST_MESSAGE
PLAYER_CLIENT_PROPERTIES_MESSAGE = ProtocolMessage.PLAYER_CLIENT_PROPERTIES_MESSAGE
REGISTER_FOR_GAME_CONTROLLER_EVENTS_MESSAGE = ProtocolMessage.REGISTER_FOR_GAME_CONTROLLER_EVENTS_MESSAGE
REGISTER_HID_DEVICE_MESSAGE = ProtocolMessage.REGISTER_HID_DEVICE_MESSAGE
REGISTER_HID_DEVICE_RESULT_MESSAGE = ProtocolMessage.REGISTER_HID_DEVICE_RESULT_MESSAGE
REGISTER_VOICE_INPUT_DEVICE_MESSAGE = ProtocolMessage.REGISTER_VOICE_INPUT_DEVICE_MESSAGE
REGISTER_VOICE_INPUT_DEVICE_RESPONSE_MESSAGE = ProtocolMessage.REGISTER_VOICE_INPUT_DEVICE_RESPONSE_MESSAGE
REMOTE_TEXT_INPUT_MESSAGE = ProtocolMessage.REMOTE_TEXT_INPUT_MESSAGE
REMOVE_CLIENT_MESSAGE = ProtocolMessage.REMOVE_CLIENT_MESSAGE
REMOVE_ENDPOINTS_MESSAGE = ProtocolMessage.REMOVE_ENDPOINTS_MESSAGE
REMOVE_OUTPUT_DEVICES_MESSAGE = ProtocolMessage.REMOVE_OUTPUT_DEVICES_MESSAGE
REMOVE_PLAYER_MESSAGE = ProtocolMessage.REMOVE_PLAYER_MESSAGE
SEND_BUTTON_EVENT_MESSAGE = ProtocolMessage.SEND_BUTTON_EVENT_MESSAGE
SEND_COMMAND_MESSAGE = ProtocolMessage.SEND_COMMAND_MESSAGE
SEND_COMMAND_RESULT_MESSAGE = ProtocolMessage.SEND_COMMAND_RESULT_MESSAGE
SEND_HID_EVENT_MESSAGE = ProtocolMessage.SEND_HID_EVENT_MESSAGE
SEND_PACKED_VIRTUAL_TOUCH_EVENT_MESSAGE = ProtocolMessage.SEND_PACKED_VIRTUAL_TOUCH_EVENT_MESSAGE
SEND_VOICE_INPUT_MESSAGE = ProtocolMessage.SEND_VOICE_INPUT_MESSAGE
SET_ARTWORK_MESSAGE = ProtocolMessage.SET_ARTWORK_MESSAGE
SET_CONNECTION_STATE_MESSAGE = ProtocolMessage.SET_CONNECTION_STATE_MESSAGE
SET_DEFAULT_SUPPORTED_COMMANDS_MESSAGE = ProtocolMessage.SET_DEFAULT_SUPPORTED_COMMANDS_MESSAGE
SET_DISCOVERY_MODE_MESSAGE = ProtocolMessage.SET_DISCOVERY_MODE_MESSAGE
SET_HILITE_MODE_MESSAGE = ProtocolMessage.SET_HILITE_MODE_MESSAGE
SET_NOW_PLAYING_CLIENT_MESSAGE = ProtocolMessage.SET_NOW_PLAYING_CLIENT_MESSAGE
SET_NOW_PLAYING_PLAYER_MESSAGE = ProtocolMessage.SET_NOW_PLAYING_PLAYER_MESSAGE
SET_RECORDING_STATE_MESSAGE = ProtocolMessage.SET_RECORDING_STATE_MESSAGE
SET_STATE_MESSAGE = ProtocolMessage.SET_STATE_MESSAGE
SET_VOLUME_MESSAGE = ProtocolMessage.SET_VOLUME_MESSAGE
TEXT_INPUT_MESSAGE = ProtocolMessage.TEXT_INPUT_MESSAGE
TRANSACTION_MESSAGE = ProtocolMessage.TRANSACTION_MESSAGE
UPDATE_CLIENT_MESSAGE = ProtocolMessage.UPDATE_CLIENT_MESSAGE
UPDATE_CONTENT_ITEM_ARTWORK_MESSAGE = ProtocolMessage.UPDATE_CONTENT_ITEM_ARTWORK_MESSAGE
UPDATE_CONTENT_ITEM_MESSAGE = ProtocolMessage.UPDATE_CONTENT_ITEM_MESSAGE
UPDATE_END_POINTS_MESSAGE = ProtocolMessage.UPDATE_END_POINTS_MESSAGE
UPDATE_OUTPUT_DEVICE_MESSAGE = ProtocolMessage.UPDATE_OUTPUT_DEVICE_MESSAGE
VOLUME_CONTROL_AVAILABILITY_MESSAGE = ProtocolMessage.VOLUME_CONTROL_AVAILABILITY_MESSAGE
VOLUME_CONTROL_CAPABILITIES_DID_CHANGE_MESSAGE = ProtocolMessage.VOLUME_CONTROL_CAPABILITIES_DID_CHANGE_MESSAGE
VOLUME_DID_CHANGE_MESSAGE = ProtocolMessage.VOLUME_DID_CHANGE_MESSAGE
WAKE_DEVICE_MESSAGE = ProtocolMessage.WAKE_DEVICE_MESSAGE


def _inner_message(self):
    extension = _EXTENSION_LOOKUP.get(self.type, None)
    if extension:
        return self.Extensions[extension]

    raise Exception('unknown type: ' + str(self.type))


ProtocolMessage.inner = _inner_message  # type: ignore
