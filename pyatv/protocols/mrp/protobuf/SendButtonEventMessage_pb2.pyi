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

class SendButtonEventMessage(google.protobuf.message.Message):
    DESCRIPTOR: google.protobuf.descriptor.Descriptor
    USAGEPAGE_FIELD_NUMBER: builtins.int
    USAGE_FIELD_NUMBER: builtins.int
    BUTTONDOWN_FIELD_NUMBER: builtins.int
    usagePage: builtins.int
    usage: builtins.int
    buttonDown: builtins.bool
    def __init__(self,
        *,
        usagePage: typing.Optional[builtins.int] = ...,
        usage: typing.Optional[builtins.int] = ...,
        buttonDown: typing.Optional[builtins.bool] = ...,
        ) -> None: ...
    def HasField(self, field_name: typing_extensions.Literal["buttonDown",b"buttonDown","usage",b"usage","usagePage",b"usagePage"]) -> builtins.bool: ...
    def ClearField(self, field_name: typing_extensions.Literal["buttonDown",b"buttonDown","usage",b"usage","usagePage",b"usagePage"]) -> None: ...
global___SendButtonEventMessage = SendButtonEventMessage

SENDBUTTONEVENTMESSAGE_FIELD_NUMBER: builtins.int
sendButtonEventMessage: google.protobuf.internal.extension_dict._ExtensionFieldDescriptor[pyatv.protocols.mrp.protobuf.ProtocolMessage_pb2.ProtocolMessage, global___SendButtonEventMessage]
