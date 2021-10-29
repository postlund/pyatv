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

class TransactionKey(google.protobuf.message.Message):
    DESCRIPTOR: google.protobuf.descriptor.Descriptor = ...
    IDENTIFIER_FIELD_NUMBER: builtins.int
    USERDATA_FIELD_NUMBER: builtins.int
    identifier: typing.Text = ...
    userData: builtins.bytes = ...
    def __init__(self,
        *,
        identifier : typing.Optional[typing.Text] = ...,
        userData : typing.Optional[builtins.bytes] = ...,
        ) -> None: ...
    def HasField(self, field_name: typing_extensions.Literal["identifier",b"identifier","userData",b"userData"]) -> builtins.bool: ...
    def ClearField(self, field_name: typing_extensions.Literal["identifier",b"identifier","userData",b"userData"]) -> None: ...
global___TransactionKey = TransactionKey
