# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: pyatv/mrp/protobuf/SetConnectionStateMessage.proto

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
  name='pyatv/mrp/protobuf/SetConnectionStateMessage.proto',
  package='',
  syntax='proto2',
  serialized_options=None,
  serialized_pb=_b('\n2pyatv/mrp/protobuf/SetConnectionStateMessage.proto\x1a(pyatv/mrp/protobuf/ProtocolMessage.proto\"x\n\x19SetConnectionStateMessage\x12\x39\n\x05state\x18\x01 \x01(\x0e\x32*.SetConnectionStateMessage.ConnectionState\" \n\x0f\x43onnectionState\x12\r\n\tConnected\x10\x02:O\n\x19setConnectionStateMessage\x12\x10.ProtocolMessage\x18* \x01(\x0b\x32\x1a.SetConnectionStateMessage')
  ,
  dependencies=[pyatv_dot_mrp_dot_protobuf_dot_ProtocolMessage__pb2.DESCRIPTOR,])


SETCONNECTIONSTATEMESSAGE_FIELD_NUMBER = 42
setConnectionStateMessage = _descriptor.FieldDescriptor(
  name='setConnectionStateMessage', full_name='setConnectionStateMessage', index=0,
  number=42, type=11, cpp_type=10, label=1,
  has_default_value=False, default_value=None,
  message_type=None, enum_type=None, containing_type=None,
  is_extension=True, extension_scope=None,
  serialized_options=None, file=DESCRIPTOR)

_SETCONNECTIONSTATEMESSAGE_CONNECTIONSTATE = _descriptor.EnumDescriptor(
  name='ConnectionState',
  full_name='SetConnectionStateMessage.ConnectionState',
  filename=None,
  file=DESCRIPTOR,
  values=[
    _descriptor.EnumValueDescriptor(
      name='Connected', index=0, number=2,
      serialized_options=None,
      type=None),
  ],
  containing_type=None,
  serialized_options=None,
  serialized_start=184,
  serialized_end=216,
)
_sym_db.RegisterEnumDescriptor(_SETCONNECTIONSTATEMESSAGE_CONNECTIONSTATE)


_SETCONNECTIONSTATEMESSAGE = _descriptor.Descriptor(
  name='SetConnectionStateMessage',
  full_name='SetConnectionStateMessage',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='state', full_name='SetConnectionStateMessage.state', index=0,
      number=1, type=14, cpp_type=8, label=1,
      has_default_value=False, default_value=2,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
    _SETCONNECTIONSTATEMESSAGE_CONNECTIONSTATE,
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto2',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=96,
  serialized_end=216,
)

_SETCONNECTIONSTATEMESSAGE.fields_by_name['state'].enum_type = _SETCONNECTIONSTATEMESSAGE_CONNECTIONSTATE
_SETCONNECTIONSTATEMESSAGE_CONNECTIONSTATE.containing_type = _SETCONNECTIONSTATEMESSAGE
DESCRIPTOR.message_types_by_name['SetConnectionStateMessage'] = _SETCONNECTIONSTATEMESSAGE
DESCRIPTOR.extensions_by_name['setConnectionStateMessage'] = setConnectionStateMessage
_sym_db.RegisterFileDescriptor(DESCRIPTOR)

SetConnectionStateMessage = _reflection.GeneratedProtocolMessageType('SetConnectionStateMessage', (_message.Message,), {
  'DESCRIPTOR' : _SETCONNECTIONSTATEMESSAGE,
  '__module__' : 'pyatv.mrp.protobuf.SetConnectionStateMessage_pb2'
  # @@protoc_insertion_point(class_scope:SetConnectionStateMessage)
  })
_sym_db.RegisterMessage(SetConnectionStateMessage)

setConnectionStateMessage.message_type = _SETCONNECTIONSTATEMESSAGE
pyatv_dot_mrp_dot_protobuf_dot_ProtocolMessage__pb2.ProtocolMessage.RegisterExtension(setConnectionStateMessage)

# @@protoc_insertion_point(module_scope)
