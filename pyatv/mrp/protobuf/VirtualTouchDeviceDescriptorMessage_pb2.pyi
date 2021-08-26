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

class VirtualTouchDeviceDescriptor(google.protobuf.message.Message):
    DESCRIPTOR: google.protobuf.descriptor.Descriptor = ...
    ABSOLUTE_FIELD_NUMBER: builtins.int
    INTEGRATEDDISPLAY_FIELD_NUMBER: builtins.int
    SCREENSIZEWIDTH_FIELD_NUMBER: builtins.int
    SCREENSIZEHEIGHT_FIELD_NUMBER: builtins.int
    absolute: builtins.bool = ...
    integratedDisplay: builtins.bool = ...
    screenSizeWidth: builtins.float = ...
    screenSizeHeight: builtins.float = ...

    def __init__(self,
        *,
        absolute : typing.Optional[builtins.bool] = ...,
        integratedDisplay : typing.Optional[builtins.bool] = ...,
        screenSizeWidth : typing.Optional[builtins.float] = ...,
        screenSizeHeight : typing.Optional[builtins.float] = ...,
        ) -> None: ...
    def HasField(self, field_name: typing_extensions.Literal[u"absolute",b"absolute",u"integratedDisplay",b"integratedDisplay",u"screenSizeHeight",b"screenSizeHeight",u"screenSizeWidth",b"screenSizeWidth"]) -> builtins.bool: ...
    def ClearField(self, field_name: typing_extensions.Literal[u"absolute",b"absolute",u"integratedDisplay",b"integratedDisplay",u"screenSizeHeight",b"screenSizeHeight",u"screenSizeWidth",b"screenSizeWidth"]) -> None: ...
global___VirtualTouchDeviceDescriptor = VirtualTouchDeviceDescriptor
