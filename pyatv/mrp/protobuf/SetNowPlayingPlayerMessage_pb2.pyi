"""
@generated by mypy-protobuf.  Do not edit manually!
isort:skip_file
"""
import builtins
import google.protobuf.descriptor
import google.protobuf.message
import pyatv.mrp.protobuf.PlayerPath_pb2
import typing
import typing_extensions

DESCRIPTOR: google.protobuf.descriptor.FileDescriptor = ...

class SetNowPlayingPlayerMessage(google.protobuf.message.Message):
    DESCRIPTOR: google.protobuf.descriptor.Descriptor = ...
    PLAYERPATH_FIELD_NUMBER: builtins.int

    @property
    def playerPath(self) -> pyatv.mrp.protobuf.PlayerPath_pb2.PlayerPath: ...

    def __init__(self,
        *,
        playerPath : typing.Optional[pyatv.mrp.protobuf.PlayerPath_pb2.PlayerPath] = ...,
        ) -> None: ...
    def HasField(self, field_name: typing_extensions.Literal[u"playerPath",b"playerPath"]) -> builtins.bool: ...
    def ClearField(self, field_name: typing_extensions.Literal[u"playerPath",b"playerPath"]) -> None: ...
global___SetNowPlayingPlayerMessage = SetNowPlayingPlayerMessage

setNowPlayingPlayerMessage: google.protobuf.descriptor.FieldDescriptor = ...
