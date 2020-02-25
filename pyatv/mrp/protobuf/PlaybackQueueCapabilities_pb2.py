# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: pyatv/mrp/protobuf/PlaybackQueueCapabilities.proto

from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor.FileDescriptor(
  name='pyatv/mrp/protobuf/PlaybackQueueCapabilities.proto',
  package='',
  syntax='proto2',
  serialized_options=None,
  serialized_pb=b'\n2pyatv/mrp/protobuf/PlaybackQueueCapabilities.proto\"k\n\x19PlaybackQueueCapabilities\x12\x16\n\x0erequestByRange\x18\x01 \x01(\x08\x12\x1c\n\x14requestByIdentifiers\x18\x02 \x01(\x08\x12\x18\n\x10requestByRequest\x18\x03 \x01(\x08'
)




_PLAYBACKQUEUECAPABILITIES = _descriptor.Descriptor(
  name='PlaybackQueueCapabilities',
  full_name='PlaybackQueueCapabilities',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='requestByRange', full_name='PlaybackQueueCapabilities.requestByRange', index=0,
      number=1, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='requestByIdentifiers', full_name='PlaybackQueueCapabilities.requestByIdentifiers', index=1,
      number=2, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='requestByRequest', full_name='PlaybackQueueCapabilities.requestByRequest', index=2,
      number=3, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
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
  serialized_start=54,
  serialized_end=161,
)

DESCRIPTOR.message_types_by_name['PlaybackQueueCapabilities'] = _PLAYBACKQUEUECAPABILITIES
_sym_db.RegisterFileDescriptor(DESCRIPTOR)

PlaybackQueueCapabilities = _reflection.GeneratedProtocolMessageType('PlaybackQueueCapabilities', (_message.Message,), {
  'DESCRIPTOR' : _PLAYBACKQUEUECAPABILITIES,
  '__module__' : 'pyatv.mrp.protobuf.PlaybackQueueCapabilities_pb2'
  # @@protoc_insertion_point(class_scope:PlaybackQueueCapabilities)
  })
_sym_db.RegisterMessage(PlaybackQueueCapabilities)


# @@protoc_insertion_point(module_scope)
