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

class OriginClientPropertiesMessage(google.protobuf.message.Message):
    DESCRIPTOR: google.protobuf.descriptor.Descriptor = ...
    LASTPLAYINGTIMESTAMP_FIELD_NUMBER: builtins.int
    lastPlayingTimestamp: builtins.float = ...

    def __init__(self,
        *,
        lastPlayingTimestamp : typing.Optional[builtins.float] = ...,
        ) -> None: ...
    def HasField(self, field_name: typing_extensions.Literal[u"lastPlayingTimestamp",b"lastPlayingTimestamp"]) -> builtins.bool: ...
    def ClearField(self, field_name: typing_extensions.Literal[u"lastPlayingTimestamp",b"lastPlayingTimestamp"]) -> None: ...
global___OriginClientPropertiesMessage = OriginClientPropertiesMessage

originClientPropertiesMessage: google.protobuf.descriptor.FieldDescriptor = ...
