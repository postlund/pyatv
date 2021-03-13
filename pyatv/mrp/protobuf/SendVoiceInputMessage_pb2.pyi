"""
@generated by mypy-protobuf.  Do not edit manually!
isort:skip_file
"""
from google.protobuf.descriptor import (
    Descriptor as google___protobuf___descriptor___Descriptor,
    FieldDescriptor as google___protobuf___descriptor___FieldDescriptor,
    FileDescriptor as google___protobuf___descriptor___FileDescriptor,
)

from google.protobuf.internal.containers import (
    RepeatedCompositeFieldContainer as google___protobuf___internal___containers___RepeatedCompositeFieldContainer,
)

from google.protobuf.message import (
    Message as google___protobuf___message___Message,
)

from pyatv.mrp.protobuf.AudioFormatSettingsMessage_pb2 import (
    AudioFormatSettings as pyatv___mrp___protobuf___AudioFormatSettingsMessage_pb2___AudioFormatSettings,
)

from typing import (
    Iterable as typing___Iterable,
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

class AudioStreamPacketDescription(google___protobuf___message___Message):
    DESCRIPTOR: google___protobuf___descriptor___Descriptor = ...
    startOffset: builtin___int = ...
    variableFramesInPacket: builtin___int = ...
    dataByteSize: builtin___int = ...

    def __init__(self,
        *,
        startOffset : typing___Optional[builtin___int] = None,
        variableFramesInPacket : typing___Optional[builtin___int] = None,
        dataByteSize : typing___Optional[builtin___int] = None,
        ) -> None: ...
    def HasField(self, field_name: typing_extensions___Literal[u"dataByteSize",b"dataByteSize",u"startOffset",b"startOffset",u"variableFramesInPacket",b"variableFramesInPacket"]) -> builtin___bool: ...
    def ClearField(self, field_name: typing_extensions___Literal[u"dataByteSize",b"dataByteSize",u"startOffset",b"startOffset",u"variableFramesInPacket",b"variableFramesInPacket"]) -> None: ...
type___AudioStreamPacketDescription = AudioStreamPacketDescription

class AudioBuffer(google___protobuf___message___Message):
    DESCRIPTOR: google___protobuf___descriptor___Descriptor = ...
    packetCapacity: builtin___int = ...
    maximumPacketSize: builtin___int = ...
    packetCount: builtin___int = ...
    contents: builtin___bytes = ...

    @property
    def formatSettings(self) -> pyatv___mrp___protobuf___AudioFormatSettingsMessage_pb2___AudioFormatSettings: ...

    @property
    def packetDescriptions(self) -> google___protobuf___internal___containers___RepeatedCompositeFieldContainer[type___AudioStreamPacketDescription]: ...

    def __init__(self,
        *,
        formatSettings : typing___Optional[pyatv___mrp___protobuf___AudioFormatSettingsMessage_pb2___AudioFormatSettings] = None,
        packetCapacity : typing___Optional[builtin___int] = None,
        maximumPacketSize : typing___Optional[builtin___int] = None,
        packetCount : typing___Optional[builtin___int] = None,
        contents : typing___Optional[builtin___bytes] = None,
        packetDescriptions : typing___Optional[typing___Iterable[type___AudioStreamPacketDescription]] = None,
        ) -> None: ...
    def HasField(self, field_name: typing_extensions___Literal[u"contents",b"contents",u"formatSettings",b"formatSettings",u"maximumPacketSize",b"maximumPacketSize",u"packetCapacity",b"packetCapacity",u"packetCount",b"packetCount"]) -> builtin___bool: ...
    def ClearField(self, field_name: typing_extensions___Literal[u"contents",b"contents",u"formatSettings",b"formatSettings",u"maximumPacketSize",b"maximumPacketSize",u"packetCapacity",b"packetCapacity",u"packetCount",b"packetCount",u"packetDescriptions",b"packetDescriptions"]) -> None: ...
type___AudioBuffer = AudioBuffer

class AudioTime(google___protobuf___message___Message):
    DESCRIPTOR: google___protobuf___descriptor___Descriptor = ...
    timestamp: builtin___float = ...
    sampleRate: builtin___float = ...

    def __init__(self,
        *,
        timestamp : typing___Optional[builtin___float] = None,
        sampleRate : typing___Optional[builtin___float] = None,
        ) -> None: ...
    def HasField(self, field_name: typing_extensions___Literal[u"sampleRate",b"sampleRate",u"timestamp",b"timestamp"]) -> builtin___bool: ...
    def ClearField(self, field_name: typing_extensions___Literal[u"sampleRate",b"sampleRate",u"timestamp",b"timestamp"]) -> None: ...
type___AudioTime = AudioTime

class AudioDataBlock(google___protobuf___message___Message):
    DESCRIPTOR: google___protobuf___descriptor___Descriptor = ...
    gain: builtin___float = ...

    @property
    def buffer(self) -> type___AudioBuffer: ...

    @property
    def time(self) -> type___AudioTime: ...

    def __init__(self,
        *,
        buffer : typing___Optional[type___AudioBuffer] = None,
        time : typing___Optional[type___AudioTime] = None,
        gain : typing___Optional[builtin___float] = None,
        ) -> None: ...
    def HasField(self, field_name: typing_extensions___Literal[u"buffer",b"buffer",u"gain",b"gain",u"time",b"time"]) -> builtin___bool: ...
    def ClearField(self, field_name: typing_extensions___Literal[u"buffer",b"buffer",u"gain",b"gain",u"time",b"time"]) -> None: ...
type___AudioDataBlock = AudioDataBlock

class SendVoiceInputMessage(google___protobuf___message___Message):
    DESCRIPTOR: google___protobuf___descriptor___Descriptor = ...

    @property
    def dataBlock(self) -> type___AudioDataBlock: ...

    def __init__(self,
        *,
        dataBlock : typing___Optional[type___AudioDataBlock] = None,
        ) -> None: ...
    def HasField(self, field_name: typing_extensions___Literal[u"dataBlock",b"dataBlock"]) -> builtin___bool: ...
    def ClearField(self, field_name: typing_extensions___Literal[u"dataBlock",b"dataBlock"]) -> None: ...
type___SendVoiceInputMessage = SendVoiceInputMessage

sendVoiceInputMessage: google___protobuf___descriptor___FieldDescriptor = ...
