"""
@generated by mypy-protobuf.  Do not edit manually!
isort:skip_file
"""
import builtins
import google.protobuf.descriptor
import google.protobuf.internal.extension_dict
import google.protobuf.message
import pyatv.protocols.mrp.protobuf.ProtocolMessage_pb2
import typing
import typing_extensions

DESCRIPTOR: google.protobuf.descriptor.FileDescriptor

class ClientUpdatesConfigMessage(google.protobuf.message.Message):
    DESCRIPTOR: google.protobuf.descriptor.Descriptor
    ARTWORKUPDATES_FIELD_NUMBER: builtins.int
    NOWPLAYINGUPDATES_FIELD_NUMBER: builtins.int
    VOLUMEUPDATES_FIELD_NUMBER: builtins.int
    KEYBOARDUPDATES_FIELD_NUMBER: builtins.int
    OUTPUTDEVICEUPDATES_FIELD_NUMBER: builtins.int
    artworkUpdates: builtins.bool
    nowPlayingUpdates: builtins.bool
    volumeUpdates: builtins.bool
    keyboardUpdates: builtins.bool
    outputDeviceUpdates: builtins.bool
    def __init__(self,
        *,
        artworkUpdates: typing.Optional[builtins.bool] = ...,
        nowPlayingUpdates: typing.Optional[builtins.bool] = ...,
        volumeUpdates: typing.Optional[builtins.bool] = ...,
        keyboardUpdates: typing.Optional[builtins.bool] = ...,
        outputDeviceUpdates: typing.Optional[builtins.bool] = ...,
        ) -> None: ...
    def HasField(self, field_name: typing_extensions.Literal["artworkUpdates",b"artworkUpdates","keyboardUpdates",b"keyboardUpdates","nowPlayingUpdates",b"nowPlayingUpdates","outputDeviceUpdates",b"outputDeviceUpdates","volumeUpdates",b"volumeUpdates"]) -> builtins.bool: ...
    def ClearField(self, field_name: typing_extensions.Literal["artworkUpdates",b"artworkUpdates","keyboardUpdates",b"keyboardUpdates","nowPlayingUpdates",b"nowPlayingUpdates","outputDeviceUpdates",b"outputDeviceUpdates","volumeUpdates",b"volumeUpdates"]) -> None: ...
global___ClientUpdatesConfigMessage = ClientUpdatesConfigMessage

CLIENTUPDATESCONFIGMESSAGE_FIELD_NUMBER: builtins.int
clientUpdatesConfigMessage: google.protobuf.internal.extension_dict._ExtensionFieldDescriptor[pyatv.protocols.mrp.protobuf.ProtocolMessage_pb2.ProtocolMessage, global___ClientUpdatesConfigMessage]
