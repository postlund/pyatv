"""
@generated by mypy-protobuf.  Do not edit manually!
isort:skip_file
"""
import builtins
import google.protobuf.descriptor
import google.protobuf.message
import pyatv.protocols.mrp.protobuf.TransactionKey_pb2
import typing
import typing_extensions

DESCRIPTOR: google.protobuf.descriptor.FileDescriptor

class TransactionPacket(google.protobuf.message.Message):
    DESCRIPTOR: google.protobuf.descriptor.Descriptor
    KEY_FIELD_NUMBER: builtins.int
    PACKETDATA_FIELD_NUMBER: builtins.int
    IDENTIFIER_FIELD_NUMBER: builtins.int
    TOTALLENGTH_FIELD_NUMBER: builtins.int
    TOTALWRITEPOSITION_FIELD_NUMBER: builtins.int
    @property
    def key(self) -> pyatv.protocols.mrp.protobuf.TransactionKey_pb2.TransactionKey: ...
    packetData: builtins.bytes
    identifier: typing.Text
    totalLength: builtins.int
    totalWritePosition: builtins.int
    def __init__(self,
        *,
        key: typing.Optional[pyatv.protocols.mrp.protobuf.TransactionKey_pb2.TransactionKey] = ...,
        packetData: typing.Optional[builtins.bytes] = ...,
        identifier: typing.Optional[typing.Text] = ...,
        totalLength: typing.Optional[builtins.int] = ...,
        totalWritePosition: typing.Optional[builtins.int] = ...,
        ) -> None: ...
    def HasField(self, field_name: typing_extensions.Literal["identifier",b"identifier","key",b"key","packetData",b"packetData","totalLength",b"totalLength","totalWritePosition",b"totalWritePosition"]) -> builtins.bool: ...
    def ClearField(self, field_name: typing_extensions.Literal["identifier",b"identifier","key",b"key","packetData",b"packetData","totalLength",b"totalLength","totalWritePosition",b"totalWritePosition"]) -> None: ...
global___TransactionPacket = TransactionPacket
