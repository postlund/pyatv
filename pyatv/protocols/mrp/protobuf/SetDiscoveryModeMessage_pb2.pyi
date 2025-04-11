"""
@generated by mypy-protobuf.  Do not edit manually!
isort:skip_file
"""

import builtins
import google.protobuf.descriptor
import google.protobuf.internal.extension_dict
import google.protobuf.message
import pyatv.protocols.mrp.protobuf.ProtocolMessage_pb2
import typing

DESCRIPTOR: google.protobuf.descriptor.FileDescriptor

@typing.final
class SetDiscoveryModeMessage(google.protobuf.message.Message):
    DESCRIPTOR: google.protobuf.descriptor.Descriptor

    MODE_FIELD_NUMBER: builtins.int
    FEATURES_FIELD_NUMBER: builtins.int
    mode: builtins.int
    features: builtins.int
    def __init__(
        self,
        *,
        mode: builtins.int | None = ...,
        features: builtins.int | None = ...,
    ) -> None: ...
    def HasField(self, field_name: typing.Literal["features", b"features", "mode", b"mode"]) -> builtins.bool: ...
    def ClearField(self, field_name: typing.Literal["features", b"features", "mode", b"mode"]) -> None: ...

global___SetDiscoveryModeMessage = SetDiscoveryModeMessage

SETDISCOVERYMODEMESSAGE_FIELD_NUMBER: builtins.int
setDiscoveryModeMessage: google.protobuf.internal.extension_dict._ExtensionFieldDescriptor[pyatv.protocols.mrp.protobuf.ProtocolMessage_pb2.ProtocolMessage, global___SetDiscoveryModeMessage]
