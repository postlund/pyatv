# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: pyatv/mrp/protobuf/WakeDeviceMessage.proto

import sys
_b=sys.version_info[0]<3 and (lambda x:x) or (lambda x:x.encode('latin1'))
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()


from pyatv.mrp.protobuf import ProtocolMessage_pb2 as pyatv_dot_mrp_dot_protobuf_dot_ProtocolMessage__pb2


DESCRIPTOR = _descriptor.FileDescriptor(
  name='pyatv/mrp/protobuf/WakeDeviceMessage.proto',
  package='',
  syntax='proto2',
  serialized_options=None,
  serialized_pb=_b('\n*pyatv/mrp/protobuf/WakeDeviceMessage.proto\x1a(pyatv/mrp/protobuf/ProtocolMessage.proto\"\x13\n\x11WakeDeviceMessage:?\n\x11wakeDeviceMessage\x12\x10.ProtocolMessage\x18- \x01(\x0b\x32\x12.WakeDeviceMessage')
  ,
  dependencies=[pyatv_dot_mrp_dot_protobuf_dot_ProtocolMessage__pb2.DESCRIPTOR,])


WAKEDEVICEMESSAGE_FIELD_NUMBER = 45
wakeDeviceMessage = _descriptor.FieldDescriptor(
  name='wakeDeviceMessage', full_name='wakeDeviceMessage', index=0,
  number=45, type=11, cpp_type=10, label=1,
  has_default_value=False, default_value=None,
  message_type=None, enum_type=None, containing_type=None,
  is_extension=True, extension_scope=None,
  serialized_options=None, file=DESCRIPTOR)


_WAKEDEVICEMESSAGE = _descriptor.Descriptor(
  name='WakeDeviceMessage',
  full_name='WakeDeviceMessage',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
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
  serialized_start=88,
  serialized_end=107,
)

DESCRIPTOR.message_types_by_name['WakeDeviceMessage'] = _WAKEDEVICEMESSAGE
DESCRIPTOR.extensions_by_name['wakeDeviceMessage'] = wakeDeviceMessage
_sym_db.RegisterFileDescriptor(DESCRIPTOR)

WakeDeviceMessage = _reflection.GeneratedProtocolMessageType('WakeDeviceMessage', (_message.Message,), {
  'DESCRIPTOR' : _WAKEDEVICEMESSAGE,
  '__module__' : 'pyatv.mrp.protobuf.WakeDeviceMessage_pb2'
  # @@protoc_insertion_point(class_scope:WakeDeviceMessage)
  })
_sym_db.RegisterMessage(WakeDeviceMessage)

wakeDeviceMessage.message_type = _WAKEDEVICEMESSAGE
pyatv_dot_mrp_dot_protobuf_dot_ProtocolMessage__pb2.ProtocolMessage.RegisterExtension(wakeDeviceMessage)

# @@protoc_insertion_point(module_scope)
