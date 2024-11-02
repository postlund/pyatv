"""
@generated by mypy-protobuf.  Do not edit manually!
isort:skip_file
"""

import builtins
import google.protobuf.descriptor
import google.protobuf.internal.extension_dict
import google.protobuf.message
import pyatv.protocols.mrp.protobuf.CommandInfo_pb2
import pyatv.protocols.mrp.protobuf.CommandOptions_pb2
import pyatv.protocols.mrp.protobuf.PlayerPath_pb2
import pyatv.protocols.mrp.protobuf.ProtocolMessage_pb2
import typing

DESCRIPTOR: google.protobuf.descriptor.FileDescriptor

@typing.final
class SendCommandMessage(google.protobuf.message.Message):
    DESCRIPTOR: google.protobuf.descriptor.Descriptor

    COMMAND_FIELD_NUMBER: builtins.int
    OPTIONS_FIELD_NUMBER: builtins.int
    PLAYERPATH_FIELD_NUMBER: builtins.int
    command: pyatv.protocols.mrp.protobuf.CommandInfo_pb2.Command.ValueType
    @property
    def options(self) -> pyatv.protocols.mrp.protobuf.CommandOptions_pb2.CommandOptions: ...
    @property
    def playerPath(self) -> pyatv.protocols.mrp.protobuf.PlayerPath_pb2.PlayerPath: ...
    def __init__(
        self,
        *,
        command: pyatv.protocols.mrp.protobuf.CommandInfo_pb2.Command.ValueType | None = ...,
        options: pyatv.protocols.mrp.protobuf.CommandOptions_pb2.CommandOptions | None = ...,
        playerPath: pyatv.protocols.mrp.protobuf.PlayerPath_pb2.PlayerPath | None = ...,
    ) -> None: ...
    def HasField(self, field_name: typing.Literal["command", b"command", "options", b"options", "playerPath", b"playerPath"]) -> builtins.bool: ...
    def ClearField(self, field_name: typing.Literal["command", b"command", "options", b"options", "playerPath", b"playerPath"]) -> None: ...

global___SendCommandMessage = SendCommandMessage

SENDCOMMANDMESSAGE_FIELD_NUMBER: builtins.int
sendCommandMessage: google.protobuf.internal.extension_dict._ExtensionFieldDescriptor[pyatv.protocols.mrp.protobuf.ProtocolMessage_pb2.ProtocolMessage, global___SendCommandMessage]
