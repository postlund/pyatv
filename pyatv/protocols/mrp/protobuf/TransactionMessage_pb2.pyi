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
import pyatv.protocols.mrp.protobuf.TransactionPackets_pb2
import typing
import typing_extensions

DESCRIPTOR: google.protobuf.descriptor.FileDescriptor = ...

class TransactionMessage(google.protobuf.message.Message):
    DESCRIPTOR: google.protobuf.descriptor.Descriptor = ...
    NAME_FIELD_NUMBER: builtins.int
    PACKETS_FIELD_NUMBER: builtins.int
    PLAYERPATH_FIELD_NUMBER: builtins.int
    name: builtins.int = ...
    @property
    def packets(self) -> pyatv.protocols.mrp.protobuf.TransactionPackets_pb2.TransactionPackets: ...
    @property
    def playerPath(self) -> pyatv.protocols.mrp.protobuf.PlayerPath_pb2.PlayerPath: ...
    def __init__(self,
        *,
        name : typing.Optional[builtins.int] = ...,
        packets : typing.Optional[pyatv.protocols.mrp.protobuf.TransactionPackets_pb2.TransactionPackets] = ...,
        playerPath : typing.Optional[pyatv.protocols.mrp.protobuf.PlayerPath_pb2.PlayerPath] = ...,
        ) -> None: ...
    def HasField(self, field_name: typing_extensions.Literal["name",b"name","packets",b"packets","playerPath",b"playerPath"]) -> builtins.bool: ...
    def ClearField(self, field_name: typing_extensions.Literal["name",b"name","packets",b"packets","playerPath",b"playerPath"]) -> None: ...
global___TransactionMessage = TransactionMessage

transactionMessage: google.protobuf.internal.extension_dict._ExtensionFieldDescriptor[pyatv.protocols.mrp.protobuf.ProtocolMessage_pb2.ProtocolMessage, global___TransactionMessage] = ...
