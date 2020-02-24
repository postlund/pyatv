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
    Union as typing___Union,
)

from typing_extensions import (
    Literal as typing_extensions___Literal,
)


builtin___bool = bool
builtin___bytes = bytes
builtin___float = float
builtin___int = int
if sys.version_info < (3,):
    builtin___buffer = buffer
    builtin___unicode = unicode


class NowPlayingPlayer(google___protobuf___message___Message):
    DESCRIPTOR: google___protobuf___descriptor___Descriptor = ...
    identifier = ... # type: typing___Text
    displayName = ... # type: typing___Text
    isDefaultPlayer = ... # type: builtin___bool

    def __init__(self,
        *,
        identifier : typing___Optional[typing___Text] = None,
        displayName : typing___Optional[typing___Text] = None,
        isDefaultPlayer : typing___Optional[builtin___bool] = None,
        ) -> None: ...
    if sys.version_info >= (3,):
        @classmethod
        def FromString(cls, s: builtin___bytes) -> NowPlayingPlayer: ...
    else:
        @classmethod
        def FromString(cls, s: typing___Union[builtin___bytes, builtin___buffer, builtin___unicode]) -> NowPlayingPlayer: ...
    def MergeFrom(self, other_msg: google___protobuf___message___Message) -> None: ...
    def CopyFrom(self, other_msg: google___protobuf___message___Message) -> None: ...
    def HasField(self, field_name: typing_extensions___Literal[u"displayName",b"displayName",u"identifier",b"identifier",u"isDefaultPlayer",b"isDefaultPlayer"]) -> builtin___bool: ...
    def ClearField(self, field_name: typing_extensions___Literal[u"displayName",b"displayName",u"identifier",b"identifier",u"isDefaultPlayer",b"isDefaultPlayer"]) -> None: ...
