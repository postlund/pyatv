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

class SetVolumeMessage(google.protobuf.message.Message):
    DESCRIPTOR: google.protobuf.descriptor.Descriptor
    VOLUME_FIELD_NUMBER: builtins.int
    OUTPUTDEVICEUID_FIELD_NUMBER: builtins.int
    volume: builtins.float
    outputDeviceUID: typing.Text
    def __init__(self,
        *,
        volume: typing.Optional[builtins.float] = ...,
        outputDeviceUID: typing.Optional[typing.Text] = ...,
        ) -> None: ...
    def HasField(self, field_name: typing_extensions.Literal["outputDeviceUID",b"outputDeviceUID","volume",b"volume"]) -> builtins.bool: ...
    def ClearField(self, field_name: typing_extensions.Literal["outputDeviceUID",b"outputDeviceUID","volume",b"volume"]) -> None: ...
global___SetVolumeMessage = SetVolumeMessage

SETVOLUMEMESSAGE_FIELD_NUMBER: builtins.int
setVolumeMessage: google.protobuf.internal.extension_dict._ExtensionFieldDescriptor[pyatv.protocols.mrp.protobuf.ProtocolMessage_pb2.ProtocolMessage, global___SetVolumeMessage]
