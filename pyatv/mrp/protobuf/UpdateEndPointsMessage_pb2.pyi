"""
@generated by mypy-protobuf.  Do not edit manually!
isort:skip_file
"""
import builtins
import google.protobuf.descriptor
import google.protobuf.message
import typing
import typing_extensions

DESCRIPTOR: google.protobuf.descriptor.FileDescriptor = ...

class AVEndpointDescriptor(google.protobuf.message.Message):
    DESCRIPTOR: google.protobuf.descriptor.Descriptor = ...
    NAME_FIELD_NUMBER: builtins.int
    UNIQUEIDENTIFIER_FIELD_NUMBER: builtins.int
    ISLOCALENDPOINT_FIELD_NUMBER: builtins.int
    INSTANCEIDENTIFIER_FIELD_NUMBER: builtins.int
    ISPROXYGROUPPLAYER_FIELD_NUMBER: builtins.int
    CONNECTIONTYPE_FIELD_NUMBER: builtins.int
    CANMODIFYGROUPMEMBERSHIP_FIELD_NUMBER: builtins.int
    name: typing.Text = ...
    uniqueIdentifier: typing.Text = ...
    isLocalEndpoint: builtins.bool = ...
    instanceIdentifier: typing.Text = ...
    isProxyGroupPlayer: builtins.bool = ...
    connectionType: builtins.int = ...
    canModifyGroupMembership: builtins.bool = ...

    def __init__(self,
        *,
        name : typing.Optional[typing.Text] = ...,
        uniqueIdentifier : typing.Optional[typing.Text] = ...,
        isLocalEndpoint : typing.Optional[builtins.bool] = ...,
        instanceIdentifier : typing.Optional[typing.Text] = ...,
        isProxyGroupPlayer : typing.Optional[builtins.bool] = ...,
        connectionType : typing.Optional[builtins.int] = ...,
        canModifyGroupMembership : typing.Optional[builtins.bool] = ...,
        ) -> None: ...
    def HasField(self, field_name: typing_extensions.Literal[u"canModifyGroupMembership",b"canModifyGroupMembership",u"connectionType",b"connectionType",u"instanceIdentifier",b"instanceIdentifier",u"isLocalEndpoint",b"isLocalEndpoint",u"isProxyGroupPlayer",b"isProxyGroupPlayer",u"name",b"name",u"uniqueIdentifier",b"uniqueIdentifier"]) -> builtins.bool: ...
    def ClearField(self, field_name: typing_extensions.Literal[u"canModifyGroupMembership",b"canModifyGroupMembership",u"connectionType",b"connectionType",u"instanceIdentifier",b"instanceIdentifier",u"isLocalEndpoint",b"isLocalEndpoint",u"isProxyGroupPlayer",b"isProxyGroupPlayer",u"name",b"name",u"uniqueIdentifier",b"uniqueIdentifier"]) -> None: ...
global___AVEndpointDescriptor = AVEndpointDescriptor

class UpdateEndPointsMessage(google.protobuf.message.Message):
    DESCRIPTOR: google.protobuf.descriptor.Descriptor = ...
    ENDPOINTS_FIELD_NUMBER: builtins.int
    ENDPOINTFEATURES_FIELD_NUMBER: builtins.int
    endpointFeatures: builtins.int = ...

    @property
    def endpoints(self) -> global___AVEndpointDescriptor: ...

    def __init__(self,
        *,
        endpoints : typing.Optional[global___AVEndpointDescriptor] = ...,
        endpointFeatures : typing.Optional[builtins.int] = ...,
        ) -> None: ...
    def HasField(self, field_name: typing_extensions.Literal[u"endpointFeatures",b"endpointFeatures",u"endpoints",b"endpoints"]) -> builtins.bool: ...
    def ClearField(self, field_name: typing_extensions.Literal[u"endpointFeatures",b"endpointFeatures",u"endpoints",b"endpoints"]) -> None: ...
global___UpdateEndPointsMessage = UpdateEndPointsMessage

updateEndPointsMessage: google.protobuf.descriptor.FieldDescriptor = ...
