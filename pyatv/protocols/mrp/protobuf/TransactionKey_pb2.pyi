"""
@generated by mypy-protobuf.  Do not edit manually!
isort:skip_file
"""

import builtins
import google.protobuf.descriptor
import google.protobuf.message
import typing

DESCRIPTOR: google.protobuf.descriptor.FileDescriptor

@typing.final
class TransactionKey(google.protobuf.message.Message):
    DESCRIPTOR: google.protobuf.descriptor.Descriptor

    IDENTIFIER_FIELD_NUMBER: builtins.int
    USERDATA_FIELD_NUMBER: builtins.int
    identifier: builtins.str
    userData: builtins.bytes
    def __init__(
        self,
        *,
        identifier: builtins.str | None = ...,
        userData: builtins.bytes | None = ...,
    ) -> None: ...
    def HasField(self, field_name: typing.Literal["identifier", b"identifier", "userData", b"userData"]) -> builtins.bool: ...
    def ClearField(self, field_name: typing.Literal["identifier", b"identifier", "userData", b"userData"]) -> None: ...

global___TransactionKey = TransactionKey
