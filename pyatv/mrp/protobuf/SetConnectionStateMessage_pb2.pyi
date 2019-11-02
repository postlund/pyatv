# @generated by generate_proto_mypy_stubs.py.  Do not edit!
import sys
from google.protobuf.descriptor import (
    Descriptor as google___protobuf___descriptor___Descriptor,
    EnumDescriptor as google___protobuf___descriptor___EnumDescriptor,
    FieldDescriptor as google___protobuf___descriptor___FieldDescriptor,
)

from google.protobuf.message import (
    Message as google___protobuf___message___Message,
)

from typing import (
    List as typing___List,
    Optional as typing___Optional,
    Tuple as typing___Tuple,
    cast as typing___cast,
)

from typing_extensions import (
    Literal as typing_extensions___Literal,
)


class SetConnectionStateMessage(google___protobuf___message___Message):
    DESCRIPTOR: google___protobuf___descriptor___Descriptor = ...
    class ConnectionState(int):
        DESCRIPTOR: google___protobuf___descriptor___EnumDescriptor = ...
        @classmethod
        def Name(cls, number: int) -> str: ...
        @classmethod
        def Value(cls, name: str) -> SetConnectionStateMessage.ConnectionState: ...
        @classmethod
        def keys(cls) -> typing___List[str]: ...
        @classmethod
        def values(cls) -> typing___List[SetConnectionStateMessage.ConnectionState]: ...
        @classmethod
        def items(cls) -> typing___List[typing___Tuple[str, SetConnectionStateMessage.ConnectionState]]: ...
        Connecting = typing___cast(SetConnectionStateMessage.ConnectionState, 1)
        Connected = typing___cast(SetConnectionStateMessage.ConnectionState, 2)
        Disconnected = typing___cast(SetConnectionStateMessage.ConnectionState, 3)
    Connecting = typing___cast(SetConnectionStateMessage.ConnectionState, 1)
    Connected = typing___cast(SetConnectionStateMessage.ConnectionState, 2)
    Disconnected = typing___cast(SetConnectionStateMessage.ConnectionState, 3)

    state = ... # type: SetConnectionStateMessage.ConnectionState

    def __init__(self,
        *,
        state : typing___Optional[SetConnectionStateMessage.ConnectionState] = None,
        ) -> None: ...
    @classmethod
    def FromString(cls, s: bytes) -> SetConnectionStateMessage: ...
    def MergeFrom(self, other_msg: google___protobuf___message___Message) -> None: ...
    def CopyFrom(self, other_msg: google___protobuf___message___Message) -> None: ...
    if sys.version_info >= (3,):
        def HasField(self, field_name: typing_extensions___Literal[u"state"]) -> bool: ...
        def ClearField(self, field_name: typing_extensions___Literal[u"state"]) -> None: ...
    else:
        def HasField(self, field_name: typing_extensions___Literal[u"state",b"state"]) -> bool: ...
        def ClearField(self, field_name: typing_extensions___Literal[u"state",b"state"]) -> None: ...

setConnectionStateMessage = ... # type: google___protobuf___descriptor___FieldDescriptor
