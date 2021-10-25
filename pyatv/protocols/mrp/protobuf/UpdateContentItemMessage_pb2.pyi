"""
@generated by mypy-protobuf.  Do not edit manually!
isort:skip_file
"""
import builtins
import google.protobuf.descriptor
import google.protobuf.internal.containers
import google.protobuf.internal.extension_dict
import google.protobuf.message
import pyatv.protocols.mrp.protobuf.ContentItem_pb2
import pyatv.protocols.mrp.protobuf.PlayerPath_pb2
import pyatv.protocols.mrp.protobuf.ProtocolMessage_pb2
import typing
import typing_extensions

DESCRIPTOR: google.protobuf.descriptor.FileDescriptor = ...

class UpdateContentItemMessage(google.protobuf.message.Message):
    DESCRIPTOR: google.protobuf.descriptor.Descriptor = ...
    CONTENTITEMS_FIELD_NUMBER: builtins.int
    PLAYERPATH_FIELD_NUMBER: builtins.int
    @property
    def contentItems(self) -> google.protobuf.internal.containers.RepeatedCompositeFieldContainer[pyatv.protocols.mrp.protobuf.ContentItem_pb2.ContentItem]: ...
    @property
    def playerPath(self) -> pyatv.protocols.mrp.protobuf.PlayerPath_pb2.PlayerPath: ...
    def __init__(self,
        *,
        contentItems : typing.Optional[typing.Iterable[pyatv.protocols.mrp.protobuf.ContentItem_pb2.ContentItem]] = ...,
        playerPath : typing.Optional[pyatv.protocols.mrp.protobuf.PlayerPath_pb2.PlayerPath] = ...,
        ) -> None: ...
    def HasField(self, field_name: typing_extensions.Literal["playerPath",b"playerPath"]) -> builtins.bool: ...
    def ClearField(self, field_name: typing_extensions.Literal["contentItems",b"contentItems","playerPath",b"playerPath"]) -> None: ...
global___UpdateContentItemMessage = UpdateContentItemMessage

updateContentItemMessage: google.protobuf.internal.extension_dict._ExtensionFieldDescriptor[pyatv.protocols.mrp.protobuf.ProtocolMessage_pb2.ProtocolMessage, global___UpdateContentItemMessage] = ...
