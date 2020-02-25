# @generated by generate_proto_mypy_stubs.py.  Do not edit!
import sys
from google.protobuf.descriptor import (
    Descriptor as google___protobuf___descriptor___Descriptor,
    FieldDescriptor as google___protobuf___descriptor___FieldDescriptor,
)

from google.protobuf.message import (
    Message as google___protobuf___message___Message,
)

from typing import (
    Optional as typing___Optional,
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


class ClientUpdatesConfigMessage(google___protobuf___message___Message):
    DESCRIPTOR: google___protobuf___descriptor___Descriptor = ...
    artworkUpdates = ... # type: builtin___bool
    nowPlayingUpdates = ... # type: builtin___bool
    volumeUpdates = ... # type: builtin___bool
    keyboardUpdates = ... # type: builtin___bool
    outputDeviceUpdates = ... # type: builtin___bool

    def __init__(self,
        *,
        artworkUpdates : typing___Optional[builtin___bool] = None,
        nowPlayingUpdates : typing___Optional[builtin___bool] = None,
        volumeUpdates : typing___Optional[builtin___bool] = None,
        keyboardUpdates : typing___Optional[builtin___bool] = None,
        outputDeviceUpdates : typing___Optional[builtin___bool] = None,
        ) -> None: ...
    if sys.version_info >= (3,):
        @classmethod
        def FromString(cls, s: builtin___bytes) -> ClientUpdatesConfigMessage: ...
    else:
        @classmethod
        def FromString(cls, s: typing___Union[builtin___bytes, builtin___buffer, builtin___unicode]) -> ClientUpdatesConfigMessage: ...
    def MergeFrom(self, other_msg: google___protobuf___message___Message) -> None: ...
    def CopyFrom(self, other_msg: google___protobuf___message___Message) -> None: ...
    def HasField(self, field_name: typing_extensions___Literal[u"artworkUpdates",b"artworkUpdates",u"keyboardUpdates",b"keyboardUpdates",u"nowPlayingUpdates",b"nowPlayingUpdates",u"outputDeviceUpdates",b"outputDeviceUpdates",u"volumeUpdates",b"volumeUpdates"]) -> builtin___bool: ...
    def ClearField(self, field_name: typing_extensions___Literal[u"artworkUpdates",b"artworkUpdates",u"keyboardUpdates",b"keyboardUpdates",u"nowPlayingUpdates",b"nowPlayingUpdates",u"outputDeviceUpdates",b"outputDeviceUpdates",u"volumeUpdates",b"volumeUpdates"]) -> None: ...

clientUpdatesConfigMessage = ... # type: google___protobuf___descriptor___FieldDescriptor
