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

DESCRIPTOR: google.protobuf.descriptor.FileDescriptor

@typing.final
class GetVolumeMessage(google.protobuf.message.Message):
    DESCRIPTOR: google.protobuf.descriptor.Descriptor

    OUTPUTDEVICEUID_FIELD_NUMBER: builtins.int
    outputDeviceUID: builtins.str
    def __init__(
        self,
        *,
        outputDeviceUID: builtins.str | None = ...,
    ) -> None: ...
    def HasField(self, field_name: typing.Literal["outputDeviceUID", b"outputDeviceUID"]) -> builtins.bool: ...
    def ClearField(self, field_name: typing.Literal["outputDeviceUID", b"outputDeviceUID"]) -> None: ...

global___GetVolumeMessage = GetVolumeMessage

GETVOLUMEMESSAGE_FIELD_NUMBER: builtins.int
getVolumeMessage: google.protobuf.internal.extension_dict._ExtensionFieldDescriptor[pyatv.protocols.mrp.protobuf.ProtocolMessage_pb2.ProtocolMessage, global___GetVolumeMessage]
