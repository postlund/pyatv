"""
@generated by mypy-protobuf.  Do not edit manually!
isort:skip_file
"""
import builtins
import google.protobuf.descriptor
import google.protobuf.internal.containers
import google.protobuf.internal.extension_dict
import google.protobuf.message
import pyatv.protocols.mrp.protobuf.AudioFormatSettingsMessage_pb2
import pyatv.protocols.mrp.protobuf.ProtocolMessage_pb2
import typing
import typing_extensions

DESCRIPTOR: google.protobuf.descriptor.FileDescriptor

class AudioStreamPacketDescription(google.protobuf.message.Message):
    DESCRIPTOR: google.protobuf.descriptor.Descriptor
    STARTOFFSET_FIELD_NUMBER: builtins.int
    VARIABLEFRAMESINPACKET_FIELD_NUMBER: builtins.int
    DATABYTESIZE_FIELD_NUMBER: builtins.int
    startOffset: builtins.int
    variableFramesInPacket: builtins.int
    dataByteSize: builtins.int
    def __init__(self,
        *,
        startOffset: typing.Optional[builtins.int] = ...,
        variableFramesInPacket: typing.Optional[builtins.int] = ...,
        dataByteSize: typing.Optional[builtins.int] = ...,
        ) -> None: ...
    def HasField(self, field_name: typing_extensions.Literal["dataByteSize",b"dataByteSize","startOffset",b"startOffset","variableFramesInPacket",b"variableFramesInPacket"]) -> builtins.bool: ...
    def ClearField(self, field_name: typing_extensions.Literal["dataByteSize",b"dataByteSize","startOffset",b"startOffset","variableFramesInPacket",b"variableFramesInPacket"]) -> None: ...
global___AudioStreamPacketDescription = AudioStreamPacketDescription

class AudioBuffer(google.protobuf.message.Message):
    DESCRIPTOR: google.protobuf.descriptor.Descriptor
    FORMATSETTINGS_FIELD_NUMBER: builtins.int
    PACKETCAPACITY_FIELD_NUMBER: builtins.int
    MAXIMUMPACKETSIZE_FIELD_NUMBER: builtins.int
    PACKETCOUNT_FIELD_NUMBER: builtins.int
    CONTENTS_FIELD_NUMBER: builtins.int
    PACKETDESCRIPTIONS_FIELD_NUMBER: builtins.int
    @property
    def formatSettings(self) -> pyatv.protocols.mrp.protobuf.AudioFormatSettingsMessage_pb2.AudioFormatSettings: ...
    packetCapacity: builtins.int
    maximumPacketSize: builtins.int
    packetCount: builtins.int
    contents: builtins.bytes
    @property
    def packetDescriptions(self) -> google.protobuf.internal.containers.RepeatedCompositeFieldContainer[global___AudioStreamPacketDescription]: ...
    def __init__(self,
        *,
        formatSettings: typing.Optional[pyatv.protocols.mrp.protobuf.AudioFormatSettingsMessage_pb2.AudioFormatSettings] = ...,
        packetCapacity: typing.Optional[builtins.int] = ...,
        maximumPacketSize: typing.Optional[builtins.int] = ...,
        packetCount: typing.Optional[builtins.int] = ...,
        contents: typing.Optional[builtins.bytes] = ...,
        packetDescriptions: typing.Optional[typing.Iterable[global___AudioStreamPacketDescription]] = ...,
        ) -> None: ...
    def HasField(self, field_name: typing_extensions.Literal["contents",b"contents","formatSettings",b"formatSettings","maximumPacketSize",b"maximumPacketSize","packetCapacity",b"packetCapacity","packetCount",b"packetCount"]) -> builtins.bool: ...
    def ClearField(self, field_name: typing_extensions.Literal["contents",b"contents","formatSettings",b"formatSettings","maximumPacketSize",b"maximumPacketSize","packetCapacity",b"packetCapacity","packetCount",b"packetCount","packetDescriptions",b"packetDescriptions"]) -> None: ...
global___AudioBuffer = AudioBuffer

class AudioTime(google.protobuf.message.Message):
    DESCRIPTOR: google.protobuf.descriptor.Descriptor
    TIMESTAMP_FIELD_NUMBER: builtins.int
    SAMPLERATE_FIELD_NUMBER: builtins.int
    timestamp: builtins.float
    sampleRate: builtins.float
    def __init__(self,
        *,
        timestamp: typing.Optional[builtins.float] = ...,
        sampleRate: typing.Optional[builtins.float] = ...,
        ) -> None: ...
    def HasField(self, field_name: typing_extensions.Literal["sampleRate",b"sampleRate","timestamp",b"timestamp"]) -> builtins.bool: ...
    def ClearField(self, field_name: typing_extensions.Literal["sampleRate",b"sampleRate","timestamp",b"timestamp"]) -> None: ...
global___AudioTime = AudioTime

class AudioDataBlock(google.protobuf.message.Message):
    DESCRIPTOR: google.protobuf.descriptor.Descriptor
    BUFFER_FIELD_NUMBER: builtins.int
    TIME_FIELD_NUMBER: builtins.int
    GAIN_FIELD_NUMBER: builtins.int
    @property
    def buffer(self) -> global___AudioBuffer: ...
    @property
    def time(self) -> global___AudioTime: ...
    gain: builtins.float
    def __init__(self,
        *,
        buffer: typing.Optional[global___AudioBuffer] = ...,
        time: typing.Optional[global___AudioTime] = ...,
        gain: typing.Optional[builtins.float] = ...,
        ) -> None: ...
    def HasField(self, field_name: typing_extensions.Literal["buffer",b"buffer","gain",b"gain","time",b"time"]) -> builtins.bool: ...
    def ClearField(self, field_name: typing_extensions.Literal["buffer",b"buffer","gain",b"gain","time",b"time"]) -> None: ...
global___AudioDataBlock = AudioDataBlock

class SendVoiceInputMessage(google.protobuf.message.Message):
    DESCRIPTOR: google.protobuf.descriptor.Descriptor
    DATABLOCK_FIELD_NUMBER: builtins.int
    @property
    def dataBlock(self) -> global___AudioDataBlock: ...
    def __init__(self,
        *,
        dataBlock: typing.Optional[global___AudioDataBlock] = ...,
        ) -> None: ...
    def HasField(self, field_name: typing_extensions.Literal["dataBlock",b"dataBlock"]) -> builtins.bool: ...
    def ClearField(self, field_name: typing_extensions.Literal["dataBlock",b"dataBlock"]) -> None: ...
global___SendVoiceInputMessage = SendVoiceInputMessage

SENDVOICEINPUTMESSAGE_FIELD_NUMBER: builtins.int
sendVoiceInputMessage: google.protobuf.internal.extension_dict._ExtensionFieldDescriptor[pyatv.protocols.mrp.protobuf.ProtocolMessage_pb2.ProtocolMessage, global___SendVoiceInputMessage]
