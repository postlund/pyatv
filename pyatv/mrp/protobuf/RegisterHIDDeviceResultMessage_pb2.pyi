"""
@generated by mypy-protobuf.  Do not edit manually!
isort:skip_file
"""
import builtins
import google.protobuf.descriptor
import google.protobuf.message
import typing
import typing_extensions

DESCRIPTOR: google.protobuf.descriptor.FileDescriptor = ...

class RegisterHIDDeviceResultMessage(google.protobuf.message.Message):
    DESCRIPTOR: google.protobuf.descriptor.Descriptor = ...
    ERRORCODE_FIELD_NUMBER: builtins.int
    DEVICEIDENTIFIER_FIELD_NUMBER: builtins.int
    errorCode: builtins.int = ...
    deviceIdentifier: builtins.int = ...

    def __init__(self,
        *,
        errorCode : typing.Optional[builtins.int] = ...,
        deviceIdentifier : typing.Optional[builtins.int] = ...,
        ) -> None: ...
    def HasField(self, field_name: typing_extensions.Literal[u"deviceIdentifier",b"deviceIdentifier",u"errorCode",b"errorCode"]) -> builtins.bool: ...
    def ClearField(self, field_name: typing_extensions.Literal[u"deviceIdentifier",b"deviceIdentifier",u"errorCode",b"errorCode"]) -> None: ...
global___RegisterHIDDeviceResultMessage = RegisterHIDDeviceResultMessage

registerHIDDeviceResultMessage: google.protobuf.descriptor.FieldDescriptor = ...
