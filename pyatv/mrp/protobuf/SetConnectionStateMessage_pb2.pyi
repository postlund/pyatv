"""
@generated by mypy-protobuf.  Do not edit manually!
isort:skip_file
"""
import builtins
import google.protobuf.descriptor
import google.protobuf.internal.enum_type_wrapper
import google.protobuf.message
import typing
import typing_extensions

DESCRIPTOR: google.protobuf.descriptor.FileDescriptor = ...

class SetConnectionStateMessage(google.protobuf.message.Message):
    DESCRIPTOR: google.protobuf.descriptor.Descriptor = ...
    class ConnectionState(metaclass=_ConnectionState):
        V = typing.NewType('V', builtins.int)

    Connecting = SetConnectionStateMessage.ConnectionState.V(1)
    Connected = SetConnectionStateMessage.ConnectionState.V(2)
    Disconnected = SetConnectionStateMessage.ConnectionState.V(3)

    class _ConnectionState(google.protobuf.internal.enum_type_wrapper._EnumTypeWrapper[ConnectionState.V], builtins.type):
        DESCRIPTOR: google.protobuf.descriptor.EnumDescriptor = ...
        Connecting = SetConnectionStateMessage.ConnectionState.V(1)
        Connected = SetConnectionStateMessage.ConnectionState.V(2)
        Disconnected = SetConnectionStateMessage.ConnectionState.V(3)

    STATE_FIELD_NUMBER: builtins.int
    state: global___SetConnectionStateMessage.ConnectionState.V = ...

    def __init__(self,
        *,
        state : typing.Optional[global___SetConnectionStateMessage.ConnectionState.V] = ...,
        ) -> None: ...
    def HasField(self, field_name: typing_extensions.Literal[u"state",b"state"]) -> builtins.bool: ...
    def ClearField(self, field_name: typing_extensions.Literal[u"state",b"state"]) -> None: ...
global___SetConnectionStateMessage = SetConnectionStateMessage

setConnectionStateMessage: google.protobuf.descriptor.FieldDescriptor = ...
