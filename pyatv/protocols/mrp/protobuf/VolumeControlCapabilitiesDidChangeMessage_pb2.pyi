"""
@generated by mypy-protobuf.  Do not edit manually!
isort:skip_file
"""
import builtins
import google.protobuf.descriptor
import google.protobuf.internal.extension_dict
import google.protobuf.message
import pyatv.protocols.mrp.protobuf.ProtocolMessage_pb2
import pyatv.protocols.mrp.protobuf.VolumeControlAvailabilityMessage_pb2
import typing
import typing_extensions

DESCRIPTOR: google.protobuf.descriptor.FileDescriptor

class VolumeControlCapabilitiesDidChangeMessage(google.protobuf.message.Message):
    DESCRIPTOR: google.protobuf.descriptor.Descriptor
    CAPABILITIES_FIELD_NUMBER: builtins.int
    ENDPOINTUID_FIELD_NUMBER: builtins.int
    OUTPUTDEVICEUID_FIELD_NUMBER: builtins.int
    @property
    def capabilities(self) -> pyatv.protocols.mrp.protobuf.VolumeControlAvailabilityMessage_pb2.VolumeControlAvailabilityMessage: ...
    endpointUID: typing.Text
    outputDeviceUID: typing.Text
    def __init__(self,
        *,
        capabilities: typing.Optional[pyatv.protocols.mrp.protobuf.VolumeControlAvailabilityMessage_pb2.VolumeControlAvailabilityMessage] = ...,
        endpointUID: typing.Optional[typing.Text] = ...,
        outputDeviceUID: typing.Optional[typing.Text] = ...,
        ) -> None: ...
    def HasField(self, field_name: typing_extensions.Literal["capabilities",b"capabilities","endpointUID",b"endpointUID","outputDeviceUID",b"outputDeviceUID"]) -> builtins.bool: ...
    def ClearField(self, field_name: typing_extensions.Literal["capabilities",b"capabilities","endpointUID",b"endpointUID","outputDeviceUID",b"outputDeviceUID"]) -> None: ...
global___VolumeControlCapabilitiesDidChangeMessage = VolumeControlCapabilitiesDidChangeMessage

VOLUMECONTROLCAPABILITIESDIDCHANGEMESSAGE_FIELD_NUMBER: builtins.int
volumeControlCapabilitiesDidChangeMessage: google.protobuf.internal.extension_dict._ExtensionFieldDescriptor[pyatv.protocols.mrp.protobuf.ProtocolMessage_pb2.ProtocolMessage, global___VolumeControlCapabilitiesDidChangeMessage]
