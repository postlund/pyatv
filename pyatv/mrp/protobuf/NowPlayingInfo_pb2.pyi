# @generated by generate_proto_mypy_stubs.py.  Do not edit!
import sys
from google.protobuf.descriptor import (
    Descriptor as google___protobuf___descriptor___Descriptor,
)

from google.protobuf.message import (
    Message as google___protobuf___message___Message,
)

from pyatv.mrp.protobuf.Common_pb2 import (
    RepeatMode as pyatv___mrp___protobuf___Common_pb2___RepeatMode,
    ShuffleMode as pyatv___mrp___protobuf___Common_pb2___ShuffleMode,
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


class NowPlayingInfo(google___protobuf___message___Message):
    DESCRIPTOR: google___protobuf___descriptor___Descriptor = ...
    album = ... # type: typing___Text
    artist = ... # type: typing___Text
    duration = ... # type: builtin___float
    elapsedTime = ... # type: builtin___float
    playbackRate = ... # type: builtin___float
    repeatMode = ... # type: pyatv___mrp___protobuf___Common_pb2___RepeatMode.Enum
    shuffleMode = ... # type: pyatv___mrp___protobuf___Common_pb2___ShuffleMode.Enum
    timestamp = ... # type: builtin___float
    title = ... # type: typing___Text
    uniqueIdentifier = ... # type: builtin___int
    isExplicitTrack = ... # type: builtin___bool
    isMusicApp = ... # type: builtin___bool
    radioStationIdentifier = ... # type: builtin___int
    radioStationHash = ... # type: typing___Text
    radioStationName = ... # type: typing___Text
    artworkDataDigest = ... # type: builtin___bytes
    isAlwaysLive = ... # type: builtin___bool
    isAdvertisement = ... # type: builtin___bool

    def __init__(self,
        *,
        album : typing___Optional[typing___Text] = None,
        artist : typing___Optional[typing___Text] = None,
        duration : typing___Optional[builtin___float] = None,
        elapsedTime : typing___Optional[builtin___float] = None,
        playbackRate : typing___Optional[builtin___float] = None,
        repeatMode : typing___Optional[pyatv___mrp___protobuf___Common_pb2___RepeatMode.Enum] = None,
        shuffleMode : typing___Optional[pyatv___mrp___protobuf___Common_pb2___ShuffleMode.Enum] = None,
        timestamp : typing___Optional[builtin___float] = None,
        title : typing___Optional[typing___Text] = None,
        uniqueIdentifier : typing___Optional[builtin___int] = None,
        isExplicitTrack : typing___Optional[builtin___bool] = None,
        isMusicApp : typing___Optional[builtin___bool] = None,
        radioStationIdentifier : typing___Optional[builtin___int] = None,
        radioStationHash : typing___Optional[typing___Text] = None,
        radioStationName : typing___Optional[typing___Text] = None,
        artworkDataDigest : typing___Optional[builtin___bytes] = None,
        isAlwaysLive : typing___Optional[builtin___bool] = None,
        isAdvertisement : typing___Optional[builtin___bool] = None,
        ) -> None: ...
    if sys.version_info >= (3,):
        @classmethod
        def FromString(cls, s: builtin___bytes) -> NowPlayingInfo: ...
    else:
        @classmethod
        def FromString(cls, s: typing___Union[builtin___bytes, builtin___buffer, builtin___unicode]) -> NowPlayingInfo: ...
    def MergeFrom(self, other_msg: google___protobuf___message___Message) -> None: ...
    def CopyFrom(self, other_msg: google___protobuf___message___Message) -> None: ...
    def HasField(self, field_name: typing_extensions___Literal[u"album",b"album",u"artist",b"artist",u"artworkDataDigest",b"artworkDataDigest",u"duration",b"duration",u"elapsedTime",b"elapsedTime",u"isAdvertisement",b"isAdvertisement",u"isAlwaysLive",b"isAlwaysLive",u"isExplicitTrack",b"isExplicitTrack",u"isMusicApp",b"isMusicApp",u"playbackRate",b"playbackRate",u"radioStationHash",b"radioStationHash",u"radioStationIdentifier",b"radioStationIdentifier",u"radioStationName",b"radioStationName",u"repeatMode",b"repeatMode",u"shuffleMode",b"shuffleMode",u"timestamp",b"timestamp",u"title",b"title",u"uniqueIdentifier",b"uniqueIdentifier"]) -> builtin___bool: ...
    def ClearField(self, field_name: typing_extensions___Literal[u"album",b"album",u"artist",b"artist",u"artworkDataDigest",b"artworkDataDigest",u"duration",b"duration",u"elapsedTime",b"elapsedTime",u"isAdvertisement",b"isAdvertisement",u"isAlwaysLive",b"isAlwaysLive",u"isExplicitTrack",b"isExplicitTrack",u"isMusicApp",b"isMusicApp",u"playbackRate",b"playbackRate",u"radioStationHash",b"radioStationHash",u"radioStationIdentifier",b"radioStationIdentifier",u"radioStationName",b"radioStationName",u"repeatMode",b"repeatMode",u"shuffleMode",b"shuffleMode",u"timestamp",b"timestamp",u"title",b"title",u"uniqueIdentifier",b"uniqueIdentifier"]) -> None: ...
global___NowPlayingInfo = NowPlayingInfo
