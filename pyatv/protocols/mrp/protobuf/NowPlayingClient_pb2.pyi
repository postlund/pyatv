"""
@generated by mypy-protobuf.  Do not edit manually!
isort:skip_file
"""
import builtins
import google.protobuf.descriptor
import google.protobuf.internal.containers
import google.protobuf.message
import typing
import typing_extensions

DESCRIPTOR: google.protobuf.descriptor.FileDescriptor = ...

class NowPlayingClient(google.protobuf.message.Message):
    DESCRIPTOR: google.protobuf.descriptor.Descriptor = ...
    PROCESSIDENTIFIER_FIELD_NUMBER: builtins.int
    BUNDLEIDENTIFIER_FIELD_NUMBER: builtins.int
    PARENTAPPLICATIONBUNDLEIDENTIFIER_FIELD_NUMBER: builtins.int
    PROCESSUSERIDENTIFIER_FIELD_NUMBER: builtins.int
    NOWPLAYINGVISIBILITY_FIELD_NUMBER: builtins.int
    DISPLAYNAME_FIELD_NUMBER: builtins.int
    BUNDLEIDENTIFIERHIERARCHYS_FIELD_NUMBER: builtins.int
    processIdentifier: builtins.int = ...
    bundleIdentifier: typing.Text = ...
    parentApplicationBundleIdentifier: typing.Text = ...
    processUserIdentifier: builtins.int = ...
    nowPlayingVisibility: builtins.int = ...
    displayName: typing.Text = ...
    """   optional TintColor tintColor = 6;"""

    @property
    def bundleIdentifierHierarchys(self) -> google.protobuf.internal.containers.RepeatedScalarFieldContainer[typing.Text]: ...
    def __init__(self,
        *,
        processIdentifier : typing.Optional[builtins.int] = ...,
        bundleIdentifier : typing.Optional[typing.Text] = ...,
        parentApplicationBundleIdentifier : typing.Optional[typing.Text] = ...,
        processUserIdentifier : typing.Optional[builtins.int] = ...,
        nowPlayingVisibility : typing.Optional[builtins.int] = ...,
        displayName : typing.Optional[typing.Text] = ...,
        bundleIdentifierHierarchys : typing.Optional[typing.Iterable[typing.Text]] = ...,
        ) -> None: ...
    def HasField(self, field_name: typing_extensions.Literal["bundleIdentifier",b"bundleIdentifier","displayName",b"displayName","nowPlayingVisibility",b"nowPlayingVisibility","parentApplicationBundleIdentifier",b"parentApplicationBundleIdentifier","processIdentifier",b"processIdentifier","processUserIdentifier",b"processUserIdentifier"]) -> builtins.bool: ...
    def ClearField(self, field_name: typing_extensions.Literal["bundleIdentifier",b"bundleIdentifier","bundleIdentifierHierarchys",b"bundleIdentifierHierarchys","displayName",b"displayName","nowPlayingVisibility",b"nowPlayingVisibility","parentApplicationBundleIdentifier",b"parentApplicationBundleIdentifier","processIdentifier",b"processIdentifier","processUserIdentifier",b"processUserIdentifier"]) -> None: ...
global___NowPlayingClient = NowPlayingClient
