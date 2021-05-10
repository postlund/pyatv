"""
@generated by mypy-protobuf.  Do not edit manually!
isort:skip_file
"""
from google.protobuf.descriptor import (
    Descriptor as google___protobuf___descriptor___Descriptor,
    EnumDescriptor as google___protobuf___descriptor___EnumDescriptor,
    FieldDescriptor as google___protobuf___descriptor___FieldDescriptor,
    FileDescriptor as google___protobuf___descriptor___FileDescriptor,
)

from google.protobuf.internal.containers import (
    RepeatedScalarFieldContainer as google___protobuf___internal___containers___RepeatedScalarFieldContainer,
)

from google.protobuf.internal.enum_type_wrapper import (
    _EnumTypeWrapper as google___protobuf___internal___enum_type_wrapper____EnumTypeWrapper,
)

from google.protobuf.message import (
    Message as google___protobuf___message___Message,
)

from typing import (
    Iterable as typing___Iterable,
    NewType as typing___NewType,
    Optional as typing___Optional,
    Text as typing___Text,
    cast as typing___cast,
)

from typing_extensions import (
    Literal as typing_extensions___Literal,
)


builtin___bool = bool
builtin___bytes = bytes
builtin___float = float
builtin___int = int


DESCRIPTOR: google___protobuf___descriptor___FileDescriptor = ...

class AutocapitalizationType(google___protobuf___message___Message):
    DESCRIPTOR: google___protobuf___descriptor___Descriptor = ...
    EnumValue = typing___NewType('EnumValue', builtin___int)
    type___EnumValue = EnumValue
    Enum: _Enum
    class _Enum(google___protobuf___internal___enum_type_wrapper____EnumTypeWrapper[AutocapitalizationType.EnumValue]):
        DESCRIPTOR: google___protobuf___descriptor___EnumDescriptor = ...
        Words = typing___cast(AutocapitalizationType.EnumValue, 1)
        Sentences = typing___cast(AutocapitalizationType.EnumValue, 2)
        AllCharacters = typing___cast(AutocapitalizationType.EnumValue, 3)
    Words = typing___cast(AutocapitalizationType.EnumValue, 1)
    Sentences = typing___cast(AutocapitalizationType.EnumValue, 2)
    AllCharacters = typing___cast(AutocapitalizationType.EnumValue, 3)


    def __init__(self,
        ) -> None: ...
type___AutocapitalizationType = AutocapitalizationType

class KeyboardType(google___protobuf___message___Message):
    DESCRIPTOR: google___protobuf___descriptor___Descriptor = ...
    EnumValue = typing___NewType('EnumValue', builtin___int)
    type___EnumValue = EnumValue
    Enum: _Enum
    class _Enum(google___protobuf___internal___enum_type_wrapper____EnumTypeWrapper[KeyboardType.EnumValue]):
        DESCRIPTOR: google___protobuf___descriptor___EnumDescriptor = ...
        Default = typing___cast(KeyboardType.EnumValue, 0)
        ASCII_Capable = typing___cast(KeyboardType.EnumValue, 1)
        NumbersAndPunctuation = typing___cast(KeyboardType.EnumValue, 2)
        URL = typing___cast(KeyboardType.EnumValue, 3)
        NumberPad = typing___cast(KeyboardType.EnumValue, 4)
        PhonePad = typing___cast(KeyboardType.EnumValue, 5)
        NamePhonePad = typing___cast(KeyboardType.EnumValue, 6)
        EmailAddress = typing___cast(KeyboardType.EnumValue, 7)
        DecimalPad = typing___cast(KeyboardType.EnumValue, 8)
        Twitter = typing___cast(KeyboardType.EnumValue, 9)
        WebSearch = typing___cast(KeyboardType.EnumValue, 10)
        Alphanet = typing___cast(KeyboardType.EnumValue, 11)
        PasscodePad = typing___cast(KeyboardType.EnumValue, 12)
    Default = typing___cast(KeyboardType.EnumValue, 0)
    ASCII_Capable = typing___cast(KeyboardType.EnumValue, 1)
    NumbersAndPunctuation = typing___cast(KeyboardType.EnumValue, 2)
    URL = typing___cast(KeyboardType.EnumValue, 3)
    NumberPad = typing___cast(KeyboardType.EnumValue, 4)
    PhonePad = typing___cast(KeyboardType.EnumValue, 5)
    NamePhonePad = typing___cast(KeyboardType.EnumValue, 6)
    EmailAddress = typing___cast(KeyboardType.EnumValue, 7)
    DecimalPad = typing___cast(KeyboardType.EnumValue, 8)
    Twitter = typing___cast(KeyboardType.EnumValue, 9)
    WebSearch = typing___cast(KeyboardType.EnumValue, 10)
    Alphanet = typing___cast(KeyboardType.EnumValue, 11)
    PasscodePad = typing___cast(KeyboardType.EnumValue, 12)


    def __init__(self,
        ) -> None: ...
type___KeyboardType = KeyboardType

class ReturnKeyType(google___protobuf___message___Message):
    DESCRIPTOR: google___protobuf___descriptor___Descriptor = ...
    EnumValue = typing___NewType('EnumValue', builtin___int)
    type___EnumValue = EnumValue
    Enum: _Enum
    class _Enum(google___protobuf___internal___enum_type_wrapper____EnumTypeWrapper[ReturnKeyType.EnumValue]):
        DESCRIPTOR: google___protobuf___descriptor___EnumDescriptor = ...
        Default = typing___cast(ReturnKeyType.EnumValue, 0)
        Go = typing___cast(ReturnKeyType.EnumValue, 1)
        Google = typing___cast(ReturnKeyType.EnumValue, 2)
        Join = typing___cast(ReturnKeyType.EnumValue, 3)
        Next = typing___cast(ReturnKeyType.EnumValue, 4)
        Route = typing___cast(ReturnKeyType.EnumValue, 5)
        Search = typing___cast(ReturnKeyType.EnumValue, 6)
        Send = typing___cast(ReturnKeyType.EnumValue, 7)
        Yahoo = typing___cast(ReturnKeyType.EnumValue, 8)
        Done = typing___cast(ReturnKeyType.EnumValue, 9)
        EmergencyCall = typing___cast(ReturnKeyType.EnumValue, 10)
        Continue = typing___cast(ReturnKeyType.EnumValue, 11)
    Default = typing___cast(ReturnKeyType.EnumValue, 0)
    Go = typing___cast(ReturnKeyType.EnumValue, 1)
    Google = typing___cast(ReturnKeyType.EnumValue, 2)
    Join = typing___cast(ReturnKeyType.EnumValue, 3)
    Next = typing___cast(ReturnKeyType.EnumValue, 4)
    Route = typing___cast(ReturnKeyType.EnumValue, 5)
    Search = typing___cast(ReturnKeyType.EnumValue, 6)
    Send = typing___cast(ReturnKeyType.EnumValue, 7)
    Yahoo = typing___cast(ReturnKeyType.EnumValue, 8)
    Done = typing___cast(ReturnKeyType.EnumValue, 9)
    EmergencyCall = typing___cast(ReturnKeyType.EnumValue, 10)
    Continue = typing___cast(ReturnKeyType.EnumValue, 11)


    def __init__(self,
        ) -> None: ...
type___ReturnKeyType = ReturnKeyType

class TextInputTraits(google___protobuf___message___Message):
    DESCRIPTOR: google___protobuf___descriptor___Descriptor = ...
    autocapitalizationType: type___AutocapitalizationType.EnumValue = ...
    keyboardType: type___KeyboardType.EnumValue = ...
    returnKeyType: type___ReturnKeyType.EnumValue = ...
    autocorrection: builtin___bool = ...
    spellchecking: builtin___bool = ...
    enablesReturnKeyAutomatically: builtin___bool = ...
    secureTextEntry: builtin___bool = ...
    validTextRangeLocation: builtin___int = ...
    validTextRangeLength: builtin___int = ...
    pINEntrySeparatorIndexes: google___protobuf___internal___containers___RepeatedScalarFieldContainer[builtin___int] = ...

    def __init__(self,
        *,
        autocapitalizationType : typing___Optional[type___AutocapitalizationType.EnumValue] = None,
        keyboardType : typing___Optional[type___KeyboardType.EnumValue] = None,
        returnKeyType : typing___Optional[type___ReturnKeyType.EnumValue] = None,
        autocorrection : typing___Optional[builtin___bool] = None,
        spellchecking : typing___Optional[builtin___bool] = None,
        enablesReturnKeyAutomatically : typing___Optional[builtin___bool] = None,
        secureTextEntry : typing___Optional[builtin___bool] = None,
        validTextRangeLocation : typing___Optional[builtin___int] = None,
        validTextRangeLength : typing___Optional[builtin___int] = None,
        pINEntrySeparatorIndexes : typing___Optional[typing___Iterable[builtin___int]] = None,
        ) -> None: ...
    def HasField(self, field_name: typing_extensions___Literal[u"autocapitalizationType",b"autocapitalizationType",u"autocorrection",b"autocorrection",u"enablesReturnKeyAutomatically",b"enablesReturnKeyAutomatically",u"keyboardType",b"keyboardType",u"returnKeyType",b"returnKeyType",u"secureTextEntry",b"secureTextEntry",u"spellchecking",b"spellchecking",u"validTextRangeLength",b"validTextRangeLength",u"validTextRangeLocation",b"validTextRangeLocation"]) -> builtin___bool: ...
    def ClearField(self, field_name: typing_extensions___Literal[u"autocapitalizationType",b"autocapitalizationType",u"autocorrection",b"autocorrection",u"enablesReturnKeyAutomatically",b"enablesReturnKeyAutomatically",u"keyboardType",b"keyboardType",u"pINEntrySeparatorIndexes",b"pINEntrySeparatorIndexes",u"returnKeyType",b"returnKeyType",u"secureTextEntry",b"secureTextEntry",u"spellchecking",b"spellchecking",u"validTextRangeLength",b"validTextRangeLength",u"validTextRangeLocation",b"validTextRangeLocation"]) -> None: ...
type___TextInputTraits = TextInputTraits

class TextEditingAttributes(google___protobuf___message___Message):
    DESCRIPTOR: google___protobuf___descriptor___Descriptor = ...
    title: typing___Text = ...
    prompt: typing___Text = ...

    @property
    def inputTraits(self) -> type___TextInputTraits: ...

    def __init__(self,
        *,
        title : typing___Optional[typing___Text] = None,
        prompt : typing___Optional[typing___Text] = None,
        inputTraits : typing___Optional[type___TextInputTraits] = None,
        ) -> None: ...
    def HasField(self, field_name: typing_extensions___Literal[u"inputTraits",b"inputTraits",u"prompt",b"prompt",u"title",b"title"]) -> builtin___bool: ...
    def ClearField(self, field_name: typing_extensions___Literal[u"inputTraits",b"inputTraits",u"prompt",b"prompt",u"title",b"title"]) -> None: ...
type___TextEditingAttributes = TextEditingAttributes

class KeyboardMessage(google___protobuf___message___Message):
    DESCRIPTOR: google___protobuf___descriptor___Descriptor = ...
    state: builtin___int = ...
    encryptedTextCyphertext: builtin___bytes = ...

    @property
    def attributes(self) -> type___TextEditingAttributes: ...

    def __init__(self,
        *,
        state : typing___Optional[builtin___int] = None,
        attributes : typing___Optional[type___TextEditingAttributes] = None,
        encryptedTextCyphertext : typing___Optional[builtin___bytes] = None,
        ) -> None: ...
    def HasField(self, field_name: typing_extensions___Literal[u"attributes",b"attributes",u"encryptedTextCyphertext",b"encryptedTextCyphertext",u"state",b"state"]) -> builtin___bool: ...
    def ClearField(self, field_name: typing_extensions___Literal[u"attributes",b"attributes",u"encryptedTextCyphertext",b"encryptedTextCyphertext",u"state",b"state"]) -> None: ...
type___KeyboardMessage = KeyboardMessage

keyboardMessage: google___protobuf___descriptor___FieldDescriptor = ...
