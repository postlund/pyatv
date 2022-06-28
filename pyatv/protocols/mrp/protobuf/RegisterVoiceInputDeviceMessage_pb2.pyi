"""
@generated by mypy-protobuf.  Do not edit manually!
isort:skip_file
"""
import builtins
import google.protobuf.descriptor
import google.protobuf.internal.extension_dict
import google.protobuf.message
import pyatv.protocols.mrp.protobuf.ProtocolMessage_pb2
import pyatv.protocols.mrp.protobuf.VoiceInputDeviceDescriptorMessage_pb2
import typing
import typing_extensions

DESCRIPTOR: google.protobuf.descriptor.FileDescriptor

class RegisterVoiceInputDeviceMessage(google.protobuf.message.Message):
    DESCRIPTOR: google.protobuf.descriptor.Descriptor
    DEVICEDESCRIPTOR_FIELD_NUMBER: builtins.int
    @property
    def deviceDescriptor(self) -> pyatv.protocols.mrp.protobuf.VoiceInputDeviceDescriptorMessage_pb2.VoiceInputDeviceDescriptor: ...
    def __init__(self,
        *,
        deviceDescriptor: typing.Optional[pyatv.protocols.mrp.protobuf.VoiceInputDeviceDescriptorMessage_pb2.VoiceInputDeviceDescriptor] = ...,
        ) -> None: ...
    def HasField(self, field_name: typing_extensions.Literal["deviceDescriptor",b"deviceDescriptor"]) -> builtins.bool: ...
    def ClearField(self, field_name: typing_extensions.Literal["deviceDescriptor",b"deviceDescriptor"]) -> None: ...
global___RegisterVoiceInputDeviceMessage = RegisterVoiceInputDeviceMessage

REGISTERVOICEINPUTDEVICEMESSAGE_FIELD_NUMBER: builtins.int
registerVoiceInputDeviceMessage: google.protobuf.internal.extension_dict._ExtensionFieldDescriptor[pyatv.protocols.mrp.protobuf.ProtocolMessage_pb2.ProtocolMessage, global___RegisterVoiceInputDeviceMessage]
