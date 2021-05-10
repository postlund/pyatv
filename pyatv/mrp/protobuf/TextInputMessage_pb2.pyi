"""
@generated by mypy-protobuf.  Do not edit manually!
isort:skip_file
"""
from google.protobuf.descriptor import (
    Descriptor as google___protobuf___descriptor___Descriptor,
    EnumDescriptor as google___protobuf___descriptor___EnumDescriptor,
    FieldDescriptor as google___protobuf___descriptor___FieldDescriptor,
    FileDescriptor as google___protobuf___descriptor___FileDescriptor,
)

from google.protobuf.internal.enum_type_wrapper import (
    _EnumTypeWrapper as google___protobuf___internal___enum_type_wrapper____EnumTypeWrapper,
)

from google.protobuf.message import (
    Message as google___protobuf___message___Message,
)

from typing import (
    NewType as typing___NewType,
    Optional as typing___Optional,
    Text as typing___Text,
    cast as typing___cast,
)

from typing_extensions import (
    Literal as typing_extensions___Literal,
)


builtin___bool = bool
builtin___bytes = bytes
builtin___float = float
builtin___int = int


DESCRIPTOR: google___protobuf___descriptor___FileDescriptor = ...

class ActionType(google___protobuf___message___Message):
    DESCRIPTOR: google___protobuf___descriptor___Descriptor = ...
    EnumValue = typing___NewType('EnumValue', builtin___int)
    type___EnumValue = EnumValue
    Enum: _Enum
    class _Enum(google___protobuf___internal___enum_type_wrapper____EnumTypeWrapper[ActionType.EnumValue]):
        DESCRIPTOR: google___protobuf___descriptor___EnumDescriptor = ...
        Unknown = typing___cast(ActionType.EnumValue, 0)
        Insert = typing___cast(ActionType.EnumValue, 1)
        Set = typing___cast(ActionType.EnumValue, 2)
        Delete = typing___cast(ActionType.EnumValue, 3)
        ClearAction = typing___cast(ActionType.EnumValue, 4)
    Unknown = typing___cast(ActionType.EnumValue, 0)
    Insert = typing___cast(ActionType.EnumValue, 1)
    Set = typing___cast(ActionType.EnumValue, 2)
    Delete = typing___cast(ActionType.EnumValue, 3)
    ClearAction = typing___cast(ActionType.EnumValue, 4)


    def __init__(self,
        ) -> None: ...
type___ActionType = ActionType

class TextInputMessage(google___protobuf___message___Message):
    DESCRIPTOR: google___protobuf___descriptor___Descriptor = ...
    timestamp: builtin___float = ...
    text: typing___Text = ...
    actionType: type___ActionType.EnumValue = ...

    def __init__(self,
        *,
        timestamp : typing___Optional[builtin___float] = None,
        text : typing___Optional[typing___Text] = None,
        actionType : typing___Optional[type___ActionType.EnumValue] = None,
        ) -> None: ...
    def HasField(self, field_name: typing_extensions___Literal[u"actionType",b"actionType",u"text",b"text",u"timestamp",b"timestamp"]) -> builtin___bool: ...
    def ClearField(self, field_name: typing_extensions___Literal[u"actionType",b"actionType",u"text",b"text",u"timestamp",b"timestamp"]) -> None: ...
type___TextInputMessage = TextInputMessage

textInputMessage: google___protobuf___descriptor___FieldDescriptor = ...
