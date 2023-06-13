"""
@generated by mypy-protobuf.  Do not edit manually!
isort:skip_file
"""
import builtins
import collections.abc
import google.protobuf.descriptor
import google.protobuf.internal.containers
import google.protobuf.internal.enum_type_wrapper
import google.protobuf.internal.extension_dict
import google.protobuf.message
import pyatv.protocols.mrp.protobuf.ProtocolMessage_pb2
import sys
import typing

if sys.version_info >= (3, 10):
    import typing as typing_extensions
else:
    import typing_extensions

DESCRIPTOR: google.protobuf.descriptor.FileDescriptor

@typing_extensions.final
class ModifyOutputContextRequestType(google.protobuf.message.Message):
    DESCRIPTOR: google.protobuf.descriptor.Descriptor

    class _Enum:
        ValueType = typing.NewType("ValueType", builtins.int)
        V: typing_extensions.TypeAlias = ValueType

    class _EnumEnumTypeWrapper(google.protobuf.internal.enum_type_wrapper._EnumTypeWrapper[ModifyOutputContextRequestType._Enum.ValueType], builtins.type):  # noqa: F821
        DESCRIPTOR: google.protobuf.descriptor.EnumDescriptor
        SharedAudioPresentation: ModifyOutputContextRequestType._Enum.ValueType  # 1

    class Enum(_Enum, metaclass=_EnumEnumTypeWrapper): ...
    SharedAudioPresentation: ModifyOutputContextRequestType.Enum.ValueType  # 1

    def __init__(
        self,
    ) -> None: ...

global___ModifyOutputContextRequestType = ModifyOutputContextRequestType

@typing_extensions.final
class ModifyOutputContextRequestMessage(google.protobuf.message.Message):
    DESCRIPTOR: google.protobuf.descriptor.Descriptor

    TYPE_FIELD_NUMBER: builtins.int
    ADDINGDEVICES_FIELD_NUMBER: builtins.int
    REMOVINGDEVICES_FIELD_NUMBER: builtins.int
    SETTINGDEVICES_FIELD_NUMBER: builtins.int
    CLUSTERAWAREADDINGDEVICES_FIELD_NUMBER: builtins.int
    CLUSTERAWAREREMOVINGDEVICES_FIELD_NUMBER: builtins.int
    CLUSTERAWARESETTINGDEVICES_FIELD_NUMBER: builtins.int
    type: global___ModifyOutputContextRequestType.Enum.ValueType
    @property
    def addingDevices(self) -> google.protobuf.internal.containers.RepeatedScalarFieldContainer[builtins.str]: ...
    @property
    def removingDevices(self) -> google.protobuf.internal.containers.RepeatedScalarFieldContainer[builtins.str]: ...
    @property
    def settingDevices(self) -> google.protobuf.internal.containers.RepeatedScalarFieldContainer[builtins.str]: ...
    @property
    def clusterAwareAddingDevices(self) -> google.protobuf.internal.containers.RepeatedScalarFieldContainer[builtins.str]: ...
    @property
    def clusterAwareRemovingDevices(self) -> google.protobuf.internal.containers.RepeatedScalarFieldContainer[builtins.str]: ...
    @property
    def clusterAwareSettingDevices(self) -> google.protobuf.internal.containers.RepeatedScalarFieldContainer[builtins.str]: ...
    def __init__(
        self,
        *,
        type: global___ModifyOutputContextRequestType.Enum.ValueType | None = ...,
        addingDevices: collections.abc.Iterable[builtins.str] | None = ...,
        removingDevices: collections.abc.Iterable[builtins.str] | None = ...,
        settingDevices: collections.abc.Iterable[builtins.str] | None = ...,
        clusterAwareAddingDevices: collections.abc.Iterable[builtins.str] | None = ...,
        clusterAwareRemovingDevices: collections.abc.Iterable[builtins.str] | None = ...,
        clusterAwareSettingDevices: collections.abc.Iterable[builtins.str] | None = ...,
    ) -> None: ...
    def HasField(self, field_name: typing_extensions.Literal["type", b"type"]) -> builtins.bool: ...
    def ClearField(self, field_name: typing_extensions.Literal["addingDevices", b"addingDevices", "clusterAwareAddingDevices", b"clusterAwareAddingDevices", "clusterAwareRemovingDevices", b"clusterAwareRemovingDevices", "clusterAwareSettingDevices", b"clusterAwareSettingDevices", "removingDevices", b"removingDevices", "settingDevices", b"settingDevices", "type", b"type"]) -> None: ...

global___ModifyOutputContextRequestMessage = ModifyOutputContextRequestMessage

MODIFYOUTPUTCONTEXTREQUESTMESSAGE_FIELD_NUMBER: builtins.int
modifyOutputContextRequestMessage: google.protobuf.internal.extension_dict._ExtensionFieldDescriptor[pyatv.protocols.mrp.protobuf.ProtocolMessage_pb2.ProtocolMessage, global___ModifyOutputContextRequestMessage]
