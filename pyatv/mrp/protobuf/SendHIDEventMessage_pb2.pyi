"""
@generated by mypy-protobuf.  Do not edit manually!
isort:skip_file
"""
from google.protobuf.descriptor import (
    Descriptor as google___protobuf___descriptor___Descriptor,
    FieldDescriptor as google___protobuf___descriptor___FieldDescriptor,
    FileDescriptor as google___protobuf___descriptor___FileDescriptor,
)

from google.protobuf.message import (
    Message as google___protobuf___message___Message,
)

from typing import (
    Optional as typing___Optional,
)

from typing_extensions import (
    Literal as typing_extensions___Literal,
)


builtin___bool = bool
builtin___bytes = bytes
builtin___float = float
builtin___int = int


DESCRIPTOR: google___protobuf___descriptor___FileDescriptor = ...

class SendHIDEventMessage(google___protobuf___message___Message):
    DESCRIPTOR: google___protobuf___descriptor___Descriptor = ...
    hidEventData: builtin___bytes = ...

    def __init__(self,
        *,
        hidEventData : typing___Optional[builtin___bytes] = None,
        ) -> None: ...
    def HasField(self, field_name: typing_extensions___Literal[u"hidEventData",b"hidEventData"]) -> builtin___bool: ...
    def ClearField(self, field_name: typing_extensions___Literal[u"hidEventData",b"hidEventData"]) -> None: ...
type___SendHIDEventMessage = SendHIDEventMessage

sendHIDEventMessage: google___protobuf___descriptor___FieldDescriptor = ...
