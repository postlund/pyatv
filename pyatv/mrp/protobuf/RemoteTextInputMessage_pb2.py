# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: pyatv/mrp/protobuf/RemoteTextInputMessage.proto
"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()


from pyatv.mrp.protobuf import ProtocolMessage_pb2 as pyatv_dot_mrp_dot_protobuf_dot_ProtocolMessage__pb2


DESCRIPTOR = _descriptor.FileDescriptor(
  name='pyatv/mrp/protobuf/RemoteTextInputMessage.proto',
  package='',
  syntax='proto2',
  serialized_options=None,
  create_key=_descriptor._internal_create_key,
  serialized_pb=b'\n/pyatv/mrp/protobuf/RemoteTextInputMessage.proto\x1a(pyatv/mrp/protobuf/ProtocolMessage.proto\"J\n\x16RemoteTextInputMessage\x12\x11\n\ttimestamp\x18\x01 \x01(\x01\x12\x0f\n\x07version\x18\x02 \x01(\x04\x12\x0c\n\x04\x64\x61ta\x18\x03 \x01(\x0c:I\n\x16remoteTextInputMessage\x12\x10.ProtocolMessage\x18G \x01(\x0b\x32\x17.RemoteTextInputMessage'
  ,
  dependencies=[pyatv_dot_mrp_dot_protobuf_dot_ProtocolMessage__pb2.DESCRIPTOR,])


REMOTETEXTINPUTMESSAGE_FIELD_NUMBER = 71
remoteTextInputMessage = _descriptor.FieldDescriptor(
  name='remoteTextInputMessage', full_name='remoteTextInputMessage', index=0,
  number=71, type=11, cpp_type=10, label=1,
  has_default_value=False, default_value=None,
  message_type=None, enum_type=None, containing_type=None,
  is_extension=True, extension_scope=None,
  serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key)


_REMOTETEXTINPUTMESSAGE = _descriptor.Descriptor(
  name='RemoteTextInputMessage',
  full_name='RemoteTextInputMessage',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='timestamp', full_name='RemoteTextInputMessage.timestamp', index=0,
      number=1, type=1, cpp_type=5, label=1,
      has_default_value=False, default_value=float(0),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='version', full_name='RemoteTextInputMessage.version', index=1,
      number=2, type=4, cpp_type=4, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='data', full_name='RemoteTextInputMessage.data', index=2,
      number=3, type=12, cpp_type=9, label=1,
      has_default_value=False, default_value=b"",
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
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
  serialized_start=93,
  serialized_end=167,
)

DESCRIPTOR.message_types_by_name['RemoteTextInputMessage'] = _REMOTETEXTINPUTMESSAGE
DESCRIPTOR.extensions_by_name['remoteTextInputMessage'] = remoteTextInputMessage
_sym_db.RegisterFileDescriptor(DESCRIPTOR)

RemoteTextInputMessage = _reflection.GeneratedProtocolMessageType('RemoteTextInputMessage', (_message.Message,), {
  'DESCRIPTOR' : _REMOTETEXTINPUTMESSAGE,
  '__module__' : 'pyatv.mrp.protobuf.RemoteTextInputMessage_pb2'
  # @@protoc_insertion_point(class_scope:RemoteTextInputMessage)
  })
_sym_db.RegisterMessage(RemoteTextInputMessage)

remoteTextInputMessage.message_type = _REMOTETEXTINPUTMESSAGE
pyatv_dot_mrp_dot_protobuf_dot_ProtocolMessage__pb2.ProtocolMessage.RegisterExtension(remoteTextInputMessage)

# @@protoc_insertion_point(module_scope)
