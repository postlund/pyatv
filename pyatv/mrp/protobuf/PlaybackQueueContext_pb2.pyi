# @generated by generate_proto_mypy_stubs.py.  Do not edit!
import sys
from google.protobuf.descriptor import (
    Descriptor as google___protobuf___descriptor___Descriptor,
)

from google.protobuf.message import (
    Message as google___protobuf___message___Message,
)

from typing import (
    Optional as typing___Optional,
    Text as typing___Text,
)

from typing_extensions import (
    Literal as typing_extensions___Literal,
)


class PlaybackQueueContext(google___protobuf___message___Message):
    DESCRIPTOR: google___protobuf___descriptor___Descriptor = ...
    revision = ... # type: typing___Text

    def __init__(self,
        *,
        revision : typing___Optional[typing___Text] = None,
        ) -> None: ...
    @classmethod
    def FromString(cls, s: bytes) -> PlaybackQueueContext: ...
    def MergeFrom(self, other_msg: google___protobuf___message___Message) -> None: ...
    def CopyFrom(self, other_msg: google___protobuf___message___Message) -> None: ...
    if sys.version_info >= (3,):
        def HasField(self, field_name: typing_extensions___Literal[u"revision"]) -> bool: ...
        def ClearField(self, field_name: typing_extensions___Literal[u"revision"]) -> None: ...
    else:
        def HasField(self, field_name: typing_extensions___Literal[u"revision",b"revision"]) -> bool: ...
        def ClearField(self, field_name: typing_extensions___Literal[u"revision",b"revision"]) -> None: ...
