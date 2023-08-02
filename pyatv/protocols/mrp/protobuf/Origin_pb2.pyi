"""
@generated by mypy-protobuf.  Do not edit manually!
isort:skip_file
"""
import builtins
import google.protobuf.descriptor
import google.protobuf.internal.enum_type_wrapper
import google.protobuf.message
import pyatv.protocols.mrp.protobuf.DeviceInfoMessage_pb2
import sys
import typing

if sys.version_info >= (3, 10):
    import typing as typing_extensions
else:
    import typing_extensions

DESCRIPTOR: google.protobuf.descriptor.FileDescriptor

@typing_extensions.final
class Origin(google.protobuf.message.Message):
    DESCRIPTOR: google.protobuf.descriptor.Descriptor

    class _Type:
        ValueType = typing.NewType("ValueType", builtins.int)
        V: typing_extensions.TypeAlias = ValueType

    class _TypeEnumTypeWrapper(google.protobuf.internal.enum_type_wrapper._EnumTypeWrapper[Origin._Type.ValueType], builtins.type):  # noqa: F821
        DESCRIPTOR: google.protobuf.descriptor.EnumDescriptor
        Unknown: Origin._Type.ValueType  # 0
        Local: Origin._Type.ValueType  # 1
        Custom: Origin._Type.ValueType  # 2

    class Type(_Type, metaclass=_TypeEnumTypeWrapper): ...
    Unknown: Origin.Type.ValueType  # 0
    Local: Origin.Type.ValueType  # 1
    Custom: Origin.Type.ValueType  # 2

    TYPE_FIELD_NUMBER: builtins.int
    DISPLAYNAME_FIELD_NUMBER: builtins.int
    IDENTIFIER_FIELD_NUMBER: builtins.int
    DEVICEINFO_FIELD_NUMBER: builtins.int
    ISLOCALLYHOSTED_FIELD_NUMBER: builtins.int
    type: global___Origin.Type.ValueType
    displayName: builtins.str
    identifier: builtins.int
    @property
    def deviceInfo(self) -> pyatv.protocols.mrp.protobuf.DeviceInfoMessage_pb2.DeviceInfoMessage: ...
    isLocallyHosted: builtins.bool
    def __init__(
        self,
        *,
        type: global___Origin.Type.ValueType | None = ...,
        displayName: builtins.str | None = ...,
        identifier: builtins.int | None = ...,
        deviceInfo: pyatv.protocols.mrp.protobuf.DeviceInfoMessage_pb2.DeviceInfoMessage | None = ...,
        isLocallyHosted: builtins.bool | None = ...,
    ) -> None: ...
    def HasField(self, field_name: typing_extensions.Literal["deviceInfo", b"deviceInfo", "displayName", b"displayName", "identifier", b"identifier", "isLocallyHosted", b"isLocallyHosted", "type", b"type"]) -> builtins.bool: ...
    def ClearField(self, field_name: typing_extensions.Literal["deviceInfo", b"deviceInfo", "displayName", b"displayName", "identifier", b"identifier", "isLocallyHosted", b"isLocallyHosted", "type", b"type"]) -> None: ...

global___Origin = Origin
