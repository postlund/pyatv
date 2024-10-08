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
import typing_extensions

DESCRIPTOR: google.protobuf.descriptor.FileDescriptor

class AVEndpointDescriptor(google.protobuf.message.Message):
    DESCRIPTOR: google.protobuf.descriptor.Descriptor
    NAME_FIELD_NUMBER: builtins.int
    UNIQUEIDENTIFIER_FIELD_NUMBER: builtins.int
    ISLOCALENDPOINT_FIELD_NUMBER: builtins.int
    INSTANCEIDENTIFIER_FIELD_NUMBER: builtins.int
    ISPROXYGROUPPLAYER_FIELD_NUMBER: builtins.int
    CONNECTIONTYPE_FIELD_NUMBER: builtins.int
    CANMODIFYGROUPMEMBERSHIP_FIELD_NUMBER: builtins.int
    name: typing.Text
    uniqueIdentifier: typing.Text
    isLocalEndpoint: builtins.bool
    """repeated ... outputDevices = 3;
    optional ... designatedGroupLeader = 4;
    """

    instanceIdentifier: typing.Text
    isProxyGroupPlayer: builtins.bool
    connectionType: builtins.int
    canModifyGroupMembership: builtins.bool
    """repeated ... _personalOutputDevices = 10;"""

    def __init__(self,
        *,
        name: typing.Optional[typing.Text] = ...,
        uniqueIdentifier: typing.Optional[typing.Text] = ...,
        isLocalEndpoint: typing.Optional[builtins.bool] = ...,
        instanceIdentifier: typing.Optional[typing.Text] = ...,
        isProxyGroupPlayer: typing.Optional[builtins.bool] = ...,
        connectionType: typing.Optional[builtins.int] = ...,
        canModifyGroupMembership: typing.Optional[builtins.bool] = ...,
        ) -> None: ...
    def HasField(self, field_name: typing_extensions.Literal["canModifyGroupMembership",b"canModifyGroupMembership","connectionType",b"connectionType","instanceIdentifier",b"instanceIdentifier","isLocalEndpoint",b"isLocalEndpoint","isProxyGroupPlayer",b"isProxyGroupPlayer","name",b"name","uniqueIdentifier",b"uniqueIdentifier"]) -> builtins.bool: ...
    def ClearField(self, field_name: typing_extensions.Literal["canModifyGroupMembership",b"canModifyGroupMembership","connectionType",b"connectionType","instanceIdentifier",b"instanceIdentifier","isLocalEndpoint",b"isLocalEndpoint","isProxyGroupPlayer",b"isProxyGroupPlayer","name",b"name","uniqueIdentifier",b"uniqueIdentifier"]) -> None: ...
global___AVEndpointDescriptor = AVEndpointDescriptor

class UpdateEndPointsMessage(google.protobuf.message.Message):
    DESCRIPTOR: google.protobuf.descriptor.Descriptor
    ENDPOINTS_FIELD_NUMBER: builtins.int
    ENDPOINTFEATURES_FIELD_NUMBER: builtins.int
    @property
    def endpoints(self) -> global___AVEndpointDescriptor: ...
    endpointFeatures: builtins.int
    def __init__(self,
        *,
        endpoints: typing.Optional[global___AVEndpointDescriptor] = ...,
        endpointFeatures: typing.Optional[builtins.int] = ...,
        ) -> None: ...
    def HasField(self, field_name: typing_extensions.Literal["endpointFeatures",b"endpointFeatures","endpoints",b"endpoints"]) -> builtins.bool: ...
    def ClearField(self, field_name: typing_extensions.Literal["endpointFeatures",b"endpointFeatures","endpoints",b"endpoints"]) -> None: ...
global___UpdateEndPointsMessage = UpdateEndPointsMessage

UPDATEENDPOINTSMESSAGE_FIELD_NUMBER: builtins.int
updateEndPointsMessage: google.protobuf.internal.extension_dict._ExtensionFieldDescriptor[pyatv.protocols.mrp.protobuf.ProtocolMessage_pb2.ProtocolMessage, global___UpdateEndPointsMessage]
