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

DESCRIPTOR: google.protobuf.descriptor.FileDescriptor = ...

class OriginClientPropertiesMessage(google.protobuf.message.Message):
    DESCRIPTOR: google.protobuf.descriptor.Descriptor = ...
    LASTPLAYINGTIMESTAMP_FIELD_NUMBER: builtins.int
    lastPlayingTimestamp: builtins.float = ...
    def __init__(self,
        *,
        lastPlayingTimestamp : typing.Optional[builtins.float] = ...,
        ) -> None: ...
    def HasField(self, field_name: typing_extensions.Literal["lastPlayingTimestamp",b"lastPlayingTimestamp"]) -> builtins.bool: ...
    def ClearField(self, field_name: typing_extensions.Literal["lastPlayingTimestamp",b"lastPlayingTimestamp"]) -> None: ...
global___OriginClientPropertiesMessage = OriginClientPropertiesMessage

originClientPropertiesMessage: google.protobuf.internal.extension_dict._ExtensionFieldDescriptor[pyatv.protocols.mrp.protobuf.ProtocolMessage_pb2.ProtocolMessage, global___OriginClientPropertiesMessage] = ...
