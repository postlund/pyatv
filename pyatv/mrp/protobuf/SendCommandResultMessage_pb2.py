# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: pyatv/mrp/protobuf/SendCommandResultMessage.proto

from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()


from pyatv.mrp.protobuf import ProtocolMessage_pb2 as pyatv_dot_mrp_dot_protobuf_dot_ProtocolMessage__pb2
from pyatv.mrp.protobuf import PlayerPath_pb2 as pyatv_dot_mrp_dot_protobuf_dot_PlayerPath__pb2


DESCRIPTOR = _descriptor.FileDescriptor(
  name='pyatv/mrp/protobuf/SendCommandResultMessage.proto',
  package='',
  syntax='proto2',
  serialized_options=None,
  serialized_pb=b'\n1pyatv/mrp/protobuf/SendCommandResultMessage.proto\x1a(pyatv/mrp/protobuf/ProtocolMessage.proto\x1a#pyatv/mrp/protobuf/PlayerPath.proto\"\xea\x01\n\tSendError\"\xdc\x01\n\x04\x45num\x12\x0b\n\x07NoError\x10\x00\x12\x17\n\x13\x41pplicationNotFound\x10\x01\x12\x14\n\x10\x43onnectionFailed\x10\x02\x12\x0b\n\x07Ignored\x10\x03\x12\x1d\n\x19\x43ouldNotLaunchApplication\x10\x04\x12\x0c\n\x08TimedOut\x10\x05\x12\x16\n\x12OriginDoesNotExist\x10\x06\x12\x12\n\x0eInvalidOptions\x10\x07\x12\x15\n\x11NoCommandHandlers\x10\x08\x12\x1b\n\x17\x41pplicationNotInstalled\x10\t\"\xc0\x02\n\x13HandlerReturnStatus\"\xa8\x02\n\x04\x45num\x12\x0b\n\x07Success\x10\x00\x12\x11\n\rNoSuchContent\x10\x01\x12\x11\n\rCommandFailed\x10\x02\x12\x1e\n\x1aNoActionableNowPlayingItem\x10\n\x12\x12\n\x0e\x44\x65viceNotFound\x10\x14\x12\x0f\n\x0bUIKitLegacy\x10\x03\x12\x14\n\x10SkipAdProhibited\x10\x64\x12\x16\n\x12QueueIsUserCurated\x10\x65\x12\x1d\n\x19UserModifiedQueueDisabled\x10\x66\x12\x33\n/UserQueueModificationNotSupportedForCurrentItem\x10g\x12&\n\"SubscriptionRequiredForSharedQueue\x10h\"\xcc\x01\n\x18SendCommandResultMessage\x12\"\n\tsendError\x18\x01 \x01(\x0e\x32\x0f.SendError.Enum\x12\x36\n\x13handlerReturnStatus\x18\x02 \x01(\x0e\x32\x19.HandlerReturnStatus.Enum\x12 \n\x18handlerReturnStatusDatas\x18\x03 \x03(\x0c\x12\x11\n\tcommandID\x18\x04 \x01(\t\x12\x1f\n\nplayerPath\x18\x05 \x01(\x0b\x32\x0b.PlayerPath:M\n\x18sendCommandResultMessage\x12\x10.ProtocolMessage\x18\x07 \x01(\x0b\x32\x19.SendCommandResultMessage'
  ,
  dependencies=[pyatv_dot_mrp_dot_protobuf_dot_ProtocolMessage__pb2.DESCRIPTOR,pyatv_dot_mrp_dot_protobuf_dot_PlayerPath__pb2.DESCRIPTOR,])


SENDCOMMANDRESULTMESSAGE_FIELD_NUMBER = 7
sendCommandResultMessage = _descriptor.FieldDescriptor(
  name='sendCommandResultMessage', full_name='sendCommandResultMessage', index=0,
  number=7, type=11, cpp_type=10, label=1,
  has_default_value=False, default_value=None,
  message_type=None, enum_type=None, containing_type=None,
  is_extension=True, extension_scope=None,
  serialized_options=None, file=DESCRIPTOR)

_SENDERROR_ENUM = _descriptor.EnumDescriptor(
  name='Enum',
  full_name='SendError.Enum',
  filename=None,
  file=DESCRIPTOR,
  values=[
    _descriptor.EnumValueDescriptor(
      name='NoError', index=0, number=0,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ApplicationNotFound', index=1, number=1,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ConnectionFailed', index=2, number=2,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='Ignored', index=3, number=3,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='CouldNotLaunchApplication', index=4, number=4,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='TimedOut', index=5, number=5,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='OriginDoesNotExist', index=6, number=6,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='InvalidOptions', index=7, number=7,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='NoCommandHandlers', index=8, number=8,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ApplicationNotInstalled', index=9, number=9,
      serialized_options=None,
      type=None),
  ],
  containing_type=None,
  serialized_options=None,
  serialized_start=147,
  serialized_end=367,
)
_sym_db.RegisterEnumDescriptor(_SENDERROR_ENUM)

_HANDLERRETURNSTATUS_ENUM = _descriptor.EnumDescriptor(
  name='Enum',
  full_name='HandlerReturnStatus.Enum',
  filename=None,
  file=DESCRIPTOR,
  values=[
    _descriptor.EnumValueDescriptor(
      name='Success', index=0, number=0,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='NoSuchContent', index=1, number=1,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='CommandFailed', index=2, number=2,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='NoActionableNowPlayingItem', index=3, number=10,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='DeviceNotFound', index=4, number=20,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='UIKitLegacy', index=5, number=3,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='SkipAdProhibited', index=6, number=100,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='QueueIsUserCurated', index=7, number=101,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='UserModifiedQueueDisabled', index=8, number=102,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='UserQueueModificationNotSupportedForCurrentItem', index=9, number=103,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='SubscriptionRequiredForSharedQueue', index=10, number=104,
      serialized_options=None,
      type=None),
  ],
  containing_type=None,
  serialized_options=None,
  serialized_start=394,
  serialized_end=690,
)
_sym_db.RegisterEnumDescriptor(_HANDLERRETURNSTATUS_ENUM)


_SENDERROR = _descriptor.Descriptor(
  name='SendError',
  full_name='SendError',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
    _SENDERROR_ENUM,
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto2',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=133,
  serialized_end=367,
)


_HANDLERRETURNSTATUS = _descriptor.Descriptor(
  name='HandlerReturnStatus',
  full_name='HandlerReturnStatus',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
    _HANDLERRETURNSTATUS_ENUM,
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto2',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=370,
  serialized_end=690,
)


_SENDCOMMANDRESULTMESSAGE = _descriptor.Descriptor(
  name='SendCommandResultMessage',
  full_name='SendCommandResultMessage',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='sendError', full_name='SendCommandResultMessage.sendError', index=0,
      number=1, type=14, cpp_type=8, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='handlerReturnStatus', full_name='SendCommandResultMessage.handlerReturnStatus', index=1,
      number=2, type=14, cpp_type=8, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='handlerReturnStatusDatas', full_name='SendCommandResultMessage.handlerReturnStatusDatas', index=2,
      number=3, type=12, cpp_type=9, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='commandID', full_name='SendCommandResultMessage.commandID', index=3,
      number=4, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='playerPath', full_name='SendCommandResultMessage.playerPath', index=4,
      number=5, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto2',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=693,
  serialized_end=897,
)

_SENDERROR_ENUM.containing_type = _SENDERROR
_HANDLERRETURNSTATUS_ENUM.containing_type = _HANDLERRETURNSTATUS
_SENDCOMMANDRESULTMESSAGE.fields_by_name['sendError'].enum_type = _SENDERROR_ENUM
_SENDCOMMANDRESULTMESSAGE.fields_by_name['handlerReturnStatus'].enum_type = _HANDLERRETURNSTATUS_ENUM
_SENDCOMMANDRESULTMESSAGE.fields_by_name['playerPath'].message_type = pyatv_dot_mrp_dot_protobuf_dot_PlayerPath__pb2._PLAYERPATH
DESCRIPTOR.message_types_by_name['SendError'] = _SENDERROR
DESCRIPTOR.message_types_by_name['HandlerReturnStatus'] = _HANDLERRETURNSTATUS
DESCRIPTOR.message_types_by_name['SendCommandResultMessage'] = _SENDCOMMANDRESULTMESSAGE
DESCRIPTOR.extensions_by_name['sendCommandResultMessage'] = sendCommandResultMessage
_sym_db.RegisterFileDescriptor(DESCRIPTOR)

SendError = _reflection.GeneratedProtocolMessageType('SendError', (_message.Message,), {
  'DESCRIPTOR' : _SENDERROR,
  '__module__' : 'pyatv.mrp.protobuf.SendCommandResultMessage_pb2'
  # @@protoc_insertion_point(class_scope:SendError)
  })
_sym_db.RegisterMessage(SendError)

HandlerReturnStatus = _reflection.GeneratedProtocolMessageType('HandlerReturnStatus', (_message.Message,), {
  'DESCRIPTOR' : _HANDLERRETURNSTATUS,
  '__module__' : 'pyatv.mrp.protobuf.SendCommandResultMessage_pb2'
  # @@protoc_insertion_point(class_scope:HandlerReturnStatus)
  })
_sym_db.RegisterMessage(HandlerReturnStatus)

SendCommandResultMessage = _reflection.GeneratedProtocolMessageType('SendCommandResultMessage', (_message.Message,), {
  'DESCRIPTOR' : _SENDCOMMANDRESULTMESSAGE,
  '__module__' : 'pyatv.mrp.protobuf.SendCommandResultMessage_pb2'
  # @@protoc_insertion_point(class_scope:SendCommandResultMessage)
  })
_sym_db.RegisterMessage(SendCommandResultMessage)

sendCommandResultMessage.message_type = _SENDCOMMANDRESULTMESSAGE
pyatv_dot_mrp_dot_protobuf_dot_ProtocolMessage__pb2.ProtocolMessage.RegisterExtension(sendCommandResultMessage)

# @@protoc_insertion_point(module_scope)
