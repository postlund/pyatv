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

class AudioFormatSettings(google.protobuf.message.Message):
    DESCRIPTOR: google.protobuf.descriptor.Descriptor = ...
    FORMATSETTINGSPLISTDATA_FIELD_NUMBER: builtins.int
    formatSettingsPlistData: builtins.bytes = ...
    def __init__(self,
        *,
        formatSettingsPlistData : typing.Optional[builtins.bytes] = ...,
        ) -> None: ...
    def HasField(self, field_name: typing_extensions.Literal["formatSettingsPlistData",b"formatSettingsPlistData"]) -> builtins.bool: ...
    def ClearField(self, field_name: typing_extensions.Literal["formatSettingsPlistData",b"formatSettingsPlistData"]) -> None: ...
global___AudioFormatSettings = AudioFormatSettings
