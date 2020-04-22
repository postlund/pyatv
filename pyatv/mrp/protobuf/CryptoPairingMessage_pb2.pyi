# @generated by generate_proto_mypy_stubs.py.  Do not edit!
import sys
from google.protobuf.descriptor import (
    Descriptor as google___protobuf___descriptor___Descriptor,
    FieldDescriptor as google___protobuf___descriptor___FieldDescriptor,
)

from google.protobuf.message import (
    Message as google___protobuf___message___Message,
)

from typing import (
    Optional as typing___Optional,
    Union as typing___Union,
)

from typing_extensions import (
    Literal as typing_extensions___Literal,
)


builtin___bool = bool
builtin___bytes = bytes
builtin___float = float
builtin___int = int
if sys.version_info < (3,):
    builtin___buffer = buffer
    builtin___unicode = unicode


class CryptoPairingMessage(google___protobuf___message___Message):
    DESCRIPTOR: google___protobuf___descriptor___Descriptor = ...
    pairingData = ... # type: builtin___bytes
    status = ... # type: builtin___int
    isRetrying = ... # type: builtin___bool
    isUsingSystemPairing = ... # type: builtin___bool
    state = ... # type: builtin___int

    def __init__(self,
        *,
        pairingData : typing___Optional[builtin___bytes] = None,
        status : typing___Optional[builtin___int] = None,
        isRetrying : typing___Optional[builtin___bool] = None,
        isUsingSystemPairing : typing___Optional[builtin___bool] = None,
        state : typing___Optional[builtin___int] = None,
        ) -> None: ...
    if sys.version_info >= (3,):
        @classmethod
        def FromString(cls, s: builtin___bytes) -> CryptoPairingMessage: ...
    else:
        @classmethod
        def FromString(cls, s: typing___Union[builtin___bytes, builtin___buffer, builtin___unicode]) -> CryptoPairingMessage: ...
    def MergeFrom(self, other_msg: google___protobuf___message___Message) -> None: ...
    def CopyFrom(self, other_msg: google___protobuf___message___Message) -> None: ...
    def HasField(self, field_name: typing_extensions___Literal[u"isRetrying",b"isRetrying",u"isUsingSystemPairing",b"isUsingSystemPairing",u"pairingData",b"pairingData",u"state",b"state",u"status",b"status"]) -> builtin___bool: ...
    def ClearField(self, field_name: typing_extensions___Literal[u"isRetrying",b"isRetrying",u"isUsingSystemPairing",b"isUsingSystemPairing",u"pairingData",b"pairingData",u"state",b"state",u"status",b"status"]) -> None: ...
global___CryptoPairingMessage = CryptoPairingMessage

cryptoPairingMessage = ... # type: google___protobuf___descriptor___FieldDescriptor
