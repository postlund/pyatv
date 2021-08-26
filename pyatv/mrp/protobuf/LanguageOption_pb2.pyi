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

class LanguageOption(google.protobuf.message.Message):
    DESCRIPTOR: google.protobuf.descriptor.Descriptor = ...
    TYPE_FIELD_NUMBER: builtins.int
    LANGUAGETAG_FIELD_NUMBER: builtins.int
    CHARACTERISTICS_FIELD_NUMBER: builtins.int
    DISPLAYNAME_FIELD_NUMBER: builtins.int
    IDENTIFIER_FIELD_NUMBER: builtins.int
    type: builtins.int = ...
    languageTag: typing.Text = ...

    @property
    def characteristics(self) -> google.protobuf.internal.containers.RepeatedScalarFieldContainer[typing.Text]: ...
    displayName: typing.Text = ...
    identifier: typing.Text = ...

    def __init__(self,
        *,
        type : typing.Optional[builtins.int] = ...,
        languageTag : typing.Optional[typing.Text] = ...,
        characteristics : typing.Optional[typing.Iterable[typing.Text]] = ...,
        displayName : typing.Optional[typing.Text] = ...,
        identifier : typing.Optional[typing.Text] = ...,
        ) -> None: ...
    def HasField(self, field_name: typing_extensions.Literal[u"displayName",b"displayName",u"identifier",b"identifier",u"languageTag",b"languageTag",u"type",b"type"]) -> builtins.bool: ...
    def ClearField(self, field_name: typing_extensions.Literal[u"characteristics",b"characteristics",u"displayName",b"displayName",u"identifier",b"identifier",u"languageTag",b"languageTag",u"type",b"type"]) -> None: ...
global___LanguageOption = LanguageOption
