"""
@generated by mypy-protobuf.  Do not edit manually!
isort:skip_file
"""
import builtins
import google.protobuf.descriptor
import google.protobuf.message
import typing
import typing_extensions

DESCRIPTOR: google.protobuf.descriptor.FileDescriptor

class NowPlayingPlayer(google.protobuf.message.Message):
    DESCRIPTOR: google.protobuf.descriptor.Descriptor
    IDENTIFIER_FIELD_NUMBER: builtins.int
    DISPLAYNAME_FIELD_NUMBER: builtins.int
    ISDEFAULTPLAYER_FIELD_NUMBER: builtins.int
    AUDIOSESSIONTYPE_FIELD_NUMBER: builtins.int
    MXSESSIONIDS_FIELD_NUMBER: builtins.int
    AUDIOSESSIONID_FIELD_NUMBER: builtins.int
    ICONURL_FIELD_NUMBER: builtins.int
    identifier: typing.Text
    displayName: typing.Text
    isDefaultPlayer: builtins.bool
    audioSessionType: builtins.int
    mxSessionIDs: builtins.int
    audioSessionID: builtins.int
    iconURL: typing.Text
    def __init__(self,
        *,
        identifier: typing.Optional[typing.Text] = ...,
        displayName: typing.Optional[typing.Text] = ...,
        isDefaultPlayer: typing.Optional[builtins.bool] = ...,
        audioSessionType: typing.Optional[builtins.int] = ...,
        mxSessionIDs: typing.Optional[builtins.int] = ...,
        audioSessionID: typing.Optional[builtins.int] = ...,
        iconURL: typing.Optional[typing.Text] = ...,
        ) -> None: ...
    def HasField(self, field_name: typing_extensions.Literal["audioSessionID",b"audioSessionID","audioSessionType",b"audioSessionType","displayName",b"displayName","iconURL",b"iconURL","identifier",b"identifier","isDefaultPlayer",b"isDefaultPlayer","mxSessionIDs",b"mxSessionIDs"]) -> builtins.bool: ...
    def ClearField(self, field_name: typing_extensions.Literal["audioSessionID",b"audioSessionID","audioSessionType",b"audioSessionType","displayName",b"displayName","iconURL",b"iconURL","identifier",b"identifier","isDefaultPlayer",b"isDefaultPlayer","mxSessionIDs",b"mxSessionIDs"]) -> None: ...
global___NowPlayingPlayer = NowPlayingPlayer
