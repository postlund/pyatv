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

class RegisterVoiceInputDeviceResponseMessage(google.protobuf.message.Message):
    DESCRIPTOR: google.protobuf.descriptor.Descriptor = ...
    DEVICEID_FIELD_NUMBER: builtins.int
    ERRORCODE_FIELD_NUMBER: builtins.int
    deviceID: builtins.int = ...
    errorCode: builtins.int = ...

    def __init__(self,
        *,
        deviceID : typing.Optional[builtins.int] = ...,
        errorCode : typing.Optional[builtins.int] = ...,
        ) -> None: ...
    def HasField(self, field_name: typing_extensions.Literal[u"deviceID",b"deviceID",u"errorCode",b"errorCode"]) -> builtins.bool: ...
    def ClearField(self, field_name: typing_extensions.Literal[u"deviceID",b"deviceID",u"errorCode",b"errorCode"]) -> None: ...
global___RegisterVoiceInputDeviceResponseMessage = RegisterVoiceInputDeviceResponseMessage

registerVoiceInputDeviceResponseMessage: google.protobuf.descriptor.FieldDescriptor = ...
