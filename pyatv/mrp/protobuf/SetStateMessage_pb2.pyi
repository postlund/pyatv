# @generated by generate_proto_mypy_stubs.py.  Do not edit!
import sys
from google.protobuf.descriptor import (
    Descriptor as google___protobuf___descriptor___Descriptor,
    FieldDescriptor as google___protobuf___descriptor___FieldDescriptor,
    FileDescriptor as google___protobuf___descriptor___FileDescriptor,
)

from google.protobuf.message import (
    Message as google___protobuf___message___Message,
)

from pyatv.mrp.protobuf.Common_pb2 import (
    PlaybackState as pyatv___mrp___protobuf___Common_pb2___PlaybackState,
)

from pyatv.mrp.protobuf.NowPlayingInfo_pb2 import (
    NowPlayingInfo as pyatv___mrp___protobuf___NowPlayingInfo_pb2___NowPlayingInfo,
)

from pyatv.mrp.protobuf.PlaybackQueueCapabilities_pb2 import (
    PlaybackQueueCapabilities as pyatv___mrp___protobuf___PlaybackQueueCapabilities_pb2___PlaybackQueueCapabilities,
)

from pyatv.mrp.protobuf.PlaybackQueueRequestMessage_pb2 import (
    PlaybackQueueRequestMessage as pyatv___mrp___protobuf___PlaybackQueueRequestMessage_pb2___PlaybackQueueRequestMessage,
)

from pyatv.mrp.protobuf.PlaybackQueue_pb2 import (
    PlaybackQueue as pyatv___mrp___protobuf___PlaybackQueue_pb2___PlaybackQueue,
)

from pyatv.mrp.protobuf.PlayerPath_pb2 import (
    PlayerPath as pyatv___mrp___protobuf___PlayerPath_pb2___PlayerPath,
)

from pyatv.mrp.protobuf.SupportedCommands_pb2 import (
    SupportedCommands as pyatv___mrp___protobuf___SupportedCommands_pb2___SupportedCommands,
)

from typing import (
    Optional as typing___Optional,
    Text as typing___Text,
)

from typing_extensions import (
    Literal as typing_extensions___Literal,
)


builtin___bool = bool
builtin___bytes = bytes
builtin___float = float
builtin___int = int


DESCRIPTOR: google___protobuf___descriptor___FileDescriptor = ...

class SetStateMessage(google___protobuf___message___Message):
    DESCRIPTOR: google___protobuf___descriptor___Descriptor = ...
    displayID: typing___Text = ...
    displayName: typing___Text = ...
    playbackState: pyatv___mrp___protobuf___Common_pb2___PlaybackState.EnumValue = ...
    playbackStateTimestamp: builtin___float = ...

    @property
    def nowPlayingInfo(self) -> pyatv___mrp___protobuf___NowPlayingInfo_pb2___NowPlayingInfo: ...

    @property
    def supportedCommands(self) -> pyatv___mrp___protobuf___SupportedCommands_pb2___SupportedCommands: ...

    @property
    def playbackQueue(self) -> pyatv___mrp___protobuf___PlaybackQueue_pb2___PlaybackQueue: ...

    @property
    def playbackQueueCapabilities(self) -> pyatv___mrp___protobuf___PlaybackQueueCapabilities_pb2___PlaybackQueueCapabilities: ...

    @property
    def playerPath(self) -> pyatv___mrp___protobuf___PlayerPath_pb2___PlayerPath: ...

    @property
    def request(self) -> pyatv___mrp___protobuf___PlaybackQueueRequestMessage_pb2___PlaybackQueueRequestMessage: ...

    def __init__(self,
        *,
        nowPlayingInfo : typing___Optional[pyatv___mrp___protobuf___NowPlayingInfo_pb2___NowPlayingInfo] = None,
        supportedCommands : typing___Optional[pyatv___mrp___protobuf___SupportedCommands_pb2___SupportedCommands] = None,
        playbackQueue : typing___Optional[pyatv___mrp___protobuf___PlaybackQueue_pb2___PlaybackQueue] = None,
        displayID : typing___Optional[typing___Text] = None,
        displayName : typing___Optional[typing___Text] = None,
        playbackState : typing___Optional[pyatv___mrp___protobuf___Common_pb2___PlaybackState.EnumValue] = None,
        playbackQueueCapabilities : typing___Optional[pyatv___mrp___protobuf___PlaybackQueueCapabilities_pb2___PlaybackQueueCapabilities] = None,
        playerPath : typing___Optional[pyatv___mrp___protobuf___PlayerPath_pb2___PlayerPath] = None,
        request : typing___Optional[pyatv___mrp___protobuf___PlaybackQueueRequestMessage_pb2___PlaybackQueueRequestMessage] = None,
        playbackStateTimestamp : typing___Optional[builtin___float] = None,
        ) -> None: ...
    def HasField(self, field_name: typing_extensions___Literal[u"displayID",b"displayID",u"displayName",b"displayName",u"nowPlayingInfo",b"nowPlayingInfo",u"playbackQueue",b"playbackQueue",u"playbackQueueCapabilities",b"playbackQueueCapabilities",u"playbackState",b"playbackState",u"playbackStateTimestamp",b"playbackStateTimestamp",u"playerPath",b"playerPath",u"request",b"request",u"supportedCommands",b"supportedCommands"]) -> builtin___bool: ...
    def ClearField(self, field_name: typing_extensions___Literal[u"displayID",b"displayID",u"displayName",b"displayName",u"nowPlayingInfo",b"nowPlayingInfo",u"playbackQueue",b"playbackQueue",u"playbackQueueCapabilities",b"playbackQueueCapabilities",u"playbackState",b"playbackState",u"playbackStateTimestamp",b"playbackStateTimestamp",u"playerPath",b"playerPath",u"request",b"request",u"supportedCommands",b"supportedCommands"]) -> None: ...
type___SetStateMessage = SetStateMessage

setStateMessage: google___protobuf___descriptor___FieldDescriptor = ...
