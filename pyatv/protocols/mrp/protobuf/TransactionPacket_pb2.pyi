"""
@generated by mypy-protobuf.  Do not edit manually!
isort:skip_file
"""

import builtins
import google.protobuf.descriptor
import google.protobuf.message
import pyatv.protocols.mrp.protobuf.TransactionKey_pb2
import typing

DESCRIPTOR: google.protobuf.descriptor.FileDescriptor

@typing.final
class TransactionPacket(google.protobuf.message.Message):
    DESCRIPTOR: google.protobuf.descriptor.Descriptor

    KEY_FIELD_NUMBER: builtins.int
    PACKETDATA_FIELD_NUMBER: builtins.int
    IDENTIFIER_FIELD_NUMBER: builtins.int
    TOTALLENGTH_FIELD_NUMBER: builtins.int
    TOTALWRITEPOSITION_FIELD_NUMBER: builtins.int
    packetData: builtins.bytes
    identifier: builtins.str
    totalLength: builtins.int
    totalWritePosition: builtins.int
    @property
    def key(self) -> pyatv.protocols.mrp.protobuf.TransactionKey_pb2.TransactionKey: ...
    def __init__(
        self,
        *,
        key: pyatv.protocols.mrp.protobuf.TransactionKey_pb2.TransactionKey | None = ...,
        packetData: builtins.bytes | None = ...,
        identifier: builtins.str | None = ...,
        totalLength: builtins.int | None = ...,
        totalWritePosition: builtins.int | None = ...,
    ) -> None: ...
    def HasField(self, field_name: typing.Literal["identifier", b"identifier", "key", b"key", "packetData", b"packetData", "totalLength", b"totalLength", "totalWritePosition", b"totalWritePosition"]) -> builtins.bool: ...
    def ClearField(self, field_name: typing.Literal["identifier", b"identifier", "key", b"key", "packetData", b"packetData", "totalLength", b"totalLength", "totalWritePosition", b"totalWritePosition"]) -> None: ...

global___TransactionPacket = TransactionPacket
