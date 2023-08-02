"""
@generated by mypy-protobuf.  Do not edit manually!
isort:skip_file
"""
import builtins
import google.protobuf.descriptor
import google.protobuf.internal.extension_dict
import google.protobuf.message
import pyatv.protocols.mrp.protobuf.PlayerPath_pb2
import pyatv.protocols.mrp.protobuf.ProtocolMessage_pb2
import sys

if sys.version_info >= (3, 8):
    import typing as typing_extensions
else:
    import typing_extensions

DESCRIPTOR: google.protobuf.descriptor.FileDescriptor

@typing_extensions.final
class UpdatePlayerMessage(google.protobuf.message.Message):
    DESCRIPTOR: google.protobuf.descriptor.Descriptor

    PLAYERPATH_FIELD_NUMBER: builtins.int
    @property
    def playerPath(self) -> pyatv.protocols.mrp.protobuf.PlayerPath_pb2.PlayerPath: ...
    def __init__(
        self,
        *,
        playerPath: pyatv.protocols.mrp.protobuf.PlayerPath_pb2.PlayerPath | None = ...,
    ) -> None: ...
    def HasField(self, field_name: typing_extensions.Literal["playerPath", b"playerPath"]) -> builtins.bool: ...
    def ClearField(self, field_name: typing_extensions.Literal["playerPath", b"playerPath"]) -> None: ...

global___UpdatePlayerMessage = UpdatePlayerMessage

UPDATEPLAYERMESSAGE_FIELD_NUMBER: builtins.int
updatePlayerMessage: google.protobuf.internal.extension_dict._ExtensionFieldDescriptor[pyatv.protocols.mrp.protobuf.ProtocolMessage_pb2.ProtocolMessage, global___UpdatePlayerMessage]
