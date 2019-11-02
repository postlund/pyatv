# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: pyatv/mrp/protobuf/PlaybackQueueRequest.proto

import sys
_b=sys.version_info[0]<3 and (lambda x:x) or (lambda x:x.encode('latin1'))
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()


from pyatv.mrp.protobuf import PlaybackQueueContext_pb2 as pyatv_dot_mrp_dot_protobuf_dot_PlaybackQueueContext__pb2
from pyatv.mrp.protobuf import PlayerPath_pb2 as pyatv_dot_mrp_dot_protobuf_dot_PlayerPath__pb2


DESCRIPTOR = _descriptor.FileDescriptor(
  name='pyatv/mrp/protobuf/PlaybackQueueRequest.proto',
  package='',
  syntax='proto2',
  serialized_options=None,
  serialized_pb=_b('\n-pyatv/mrp/protobuf/PlaybackQueueRequest.proto\x1a-pyatv/mrp/protobuf/PlaybackQueueContext.proto\x1a#pyatv/mrp/protobuf/PlayerPath.proto\"\xdd\x03\n\x14PlaybackQueueRequest\x12\x10\n\x08location\x18\x01 \x01(\x05\x12\x0e\n\x06length\x18\x02 \x01(\x05\x12\x17\n\x0fincludeMetadata\x18\x03 \x01(\x08\x12\x14\n\x0c\x61rtworkWidth\x18\x04 \x01(\x01\x12\x15\n\rartworkHeight\x18\x05 \x01(\x01\x12\x15\n\rincludeLyrics\x18\x06 \x01(\x08\x12\x17\n\x0fincludeSections\x18\x07 \x01(\x08\x12\x13\n\x0bincludeInfo\x18\x08 \x01(\x08\x12\x1e\n\x16includeLanguageOptions\x18\t \x01(\x08\x12&\n\x07\x63ontext\x18\n \x01(\x0b\x32\x15.PlaybackQueueContext\x12\x11\n\trequestID\x18\x0b \x01(\t\x12\x1e\n\x16\x63ontentItemIdentifiers\x18\x0c \x03(\t\x12/\n\'returnContentItemAssetsInUserCompletion\x18\r \x01(\x08\x12\x1f\n\nplayerPath\x18\x0e \x01(\x0b\x32\x0b.PlayerPath\x12\x15\n\rcachingPolicy\x18\x0f \x01(\x05\x12\r\n\x05label\x18\x10 \x01(\t\x12%\n\x1disLegacyNowPlayingInfoRequest\x18\x11 \x01(\x08')
  ,
  dependencies=[pyatv_dot_mrp_dot_protobuf_dot_PlaybackQueueContext__pb2.DESCRIPTOR,pyatv_dot_mrp_dot_protobuf_dot_PlayerPath__pb2.DESCRIPTOR,])




_PLAYBACKQUEUEREQUEST = _descriptor.Descriptor(
  name='PlaybackQueueRequest',
  full_name='PlaybackQueueRequest',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='location', full_name='PlaybackQueueRequest.location', index=0,
      number=1, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='length', full_name='PlaybackQueueRequest.length', index=1,
      number=2, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='includeMetadata', full_name='PlaybackQueueRequest.includeMetadata', index=2,
      number=3, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='artworkWidth', full_name='PlaybackQueueRequest.artworkWidth', index=3,
      number=4, type=1, cpp_type=5, label=1,
      has_default_value=False, default_value=float(0),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='artworkHeight', full_name='PlaybackQueueRequest.artworkHeight', index=4,
      number=5, type=1, cpp_type=5, label=1,
      has_default_value=False, default_value=float(0),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='includeLyrics', full_name='PlaybackQueueRequest.includeLyrics', index=5,
      number=6, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='includeSections', full_name='PlaybackQueueRequest.includeSections', index=6,
      number=7, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='includeInfo', full_name='PlaybackQueueRequest.includeInfo', index=7,
      number=8, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='includeLanguageOptions', full_name='PlaybackQueueRequest.includeLanguageOptions', index=8,
      number=9, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='context', full_name='PlaybackQueueRequest.context', index=9,
      number=10, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='requestID', full_name='PlaybackQueueRequest.requestID', index=10,
      number=11, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='contentItemIdentifiers', full_name='PlaybackQueueRequest.contentItemIdentifiers', index=11,
      number=12, type=9, cpp_type=9, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='returnContentItemAssetsInUserCompletion', full_name='PlaybackQueueRequest.returnContentItemAssetsInUserCompletion', index=12,
      number=13, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='playerPath', full_name='PlaybackQueueRequest.playerPath', index=13,
      number=14, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='cachingPolicy', full_name='PlaybackQueueRequest.cachingPolicy', index=14,
      number=15, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='label', full_name='PlaybackQueueRequest.label', index=15,
      number=16, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='isLegacyNowPlayingInfoRequest', full_name='PlaybackQueueRequest.isLegacyNowPlayingInfoRequest', index=16,
      number=17, type=8, cpp_type=7, label=1,
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
  serialized_start=134,
  serialized_end=611,
)

_PLAYBACKQUEUEREQUEST.fields_by_name['context'].message_type = pyatv_dot_mrp_dot_protobuf_dot_PlaybackQueueContext__pb2._PLAYBACKQUEUECONTEXT
_PLAYBACKQUEUEREQUEST.fields_by_name['playerPath'].message_type = pyatv_dot_mrp_dot_protobuf_dot_PlayerPath__pb2._PLAYERPATH
DESCRIPTOR.message_types_by_name['PlaybackQueueRequest'] = _PLAYBACKQUEUEREQUEST
_sym_db.RegisterFileDescriptor(DESCRIPTOR)

PlaybackQueueRequest = _reflection.GeneratedProtocolMessageType('PlaybackQueueRequest', (_message.Message,), {
  'DESCRIPTOR' : _PLAYBACKQUEUEREQUEST,
  '__module__' : 'pyatv.mrp.protobuf.PlaybackQueueRequest_pb2'
  # @@protoc_insertion_point(class_scope:PlaybackQueueRequest)
  })
_sym_db.RegisterMessage(PlaybackQueueRequest)


# @@protoc_insertion_point(module_scope)
