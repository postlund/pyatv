# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: pyatv/mrp/protobuf/ClientUpdatesConfigMessage.proto

import sys
_b=sys.version_info[0]<3 and (lambda x:x) or (lambda x:x.encode('latin1'))
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database
from google.protobuf import descriptor_pb2
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()


from pyatv.mrp.protobuf import ProtocolMessage_pb2 as pyatv_dot_mrp_dot_protobuf_dot_ProtocolMessage__pb2


DESCRIPTOR = _descriptor.FileDescriptor(
  name='pyatv/mrp/protobuf/ClientUpdatesConfigMessage.proto',
  package='',
  syntax='proto2',
  serialized_pb=_b('\n3pyatv/mrp/protobuf/ClientUpdatesConfigMessage.proto\x1a(pyatv/mrp/protobuf/ProtocolMessage.proto\"\x7f\n\x1a\x43lientUpdatesConfigMessage\x12\x16\n\x0e\x61rtworkUpdates\x18\x01 \x01(\x08\x12\x19\n\x11nowPlayingUpdates\x18\x02 \x01(\x08\x12\x15\n\rvolumeUpdates\x18\x03 \x01(\x08\x12\x17\n\x0fkeyboardUpdates\x18\x04 \x01(\x08:Q\n\x1a\x63lientUpdatesConfigMessage\x12\x10.ProtocolMessage\x18\x15 \x01(\x0b\x32\x1b.ClientUpdatesConfigMessage')
  ,
  dependencies=[pyatv_dot_mrp_dot_protobuf_dot_ProtocolMessage__pb2.DESCRIPTOR,])


CLIENTUPDATESCONFIGMESSAGE_FIELD_NUMBER = 21
clientUpdatesConfigMessage = _descriptor.FieldDescriptor(
  name='clientUpdatesConfigMessage', full_name='clientUpdatesConfigMessage', index=0,
  number=21, type=11, cpp_type=10, label=1,
  has_default_value=False, default_value=None,
  message_type=None, enum_type=None, containing_type=None,
  is_extension=True, extension_scope=None,
  options=None)


_CLIENTUPDATESCONFIGMESSAGE = _descriptor.Descriptor(
  name='ClientUpdatesConfigMessage',
  full_name='ClientUpdatesConfigMessage',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='artworkUpdates', full_name='ClientUpdatesConfigMessage.artworkUpdates', index=0,
      number=1, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='nowPlayingUpdates', full_name='ClientUpdatesConfigMessage.nowPlayingUpdates', index=1,
      number=2, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='volumeUpdates', full_name='ClientUpdatesConfigMessage.volumeUpdates', index=2,
      number=3, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='keyboardUpdates', full_name='ClientUpdatesConfigMessage.keyboardUpdates', index=3,
      number=4, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  syntax='proto2',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=97,
  serialized_end=224,
)

DESCRIPTOR.message_types_by_name['ClientUpdatesConfigMessage'] = _CLIENTUPDATESCONFIGMESSAGE
DESCRIPTOR.extensions_by_name['clientUpdatesConfigMessage'] = clientUpdatesConfigMessage
_sym_db.RegisterFileDescriptor(DESCRIPTOR)

ClientUpdatesConfigMessage = _reflection.GeneratedProtocolMessageType('ClientUpdatesConfigMessage', (_message.Message,), dict(
  DESCRIPTOR = _CLIENTUPDATESCONFIGMESSAGE,
  __module__ = 'pyatv.mrp.protobuf.ClientUpdatesConfigMessage_pb2'
  # @@protoc_insertion_point(class_scope:ClientUpdatesConfigMessage)
  ))
_sym_db.RegisterMessage(ClientUpdatesConfigMessage)

clientUpdatesConfigMessage.message_type = _CLIENTUPDATESCONFIGMESSAGE
pyatv_dot_mrp_dot_protobuf_dot_ProtocolMessage__pb2.ProtocolMessage.RegisterExtension(clientUpdatesConfigMessage)

# @@protoc_insertion_point(module_scope)
