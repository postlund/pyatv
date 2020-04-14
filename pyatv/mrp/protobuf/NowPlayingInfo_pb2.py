# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: pyatv/mrp/protobuf/NowPlayingInfo.proto

from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()


from pyatv.mrp.protobuf import Common_pb2 as pyatv_dot_mrp_dot_protobuf_dot_Common__pb2


DESCRIPTOR = _descriptor.FileDescriptor(
  name='pyatv/mrp/protobuf/NowPlayingInfo.proto',
  package='',
  syntax='proto2',
  serialized_options=None,
  serialized_pb=b'\n\'pyatv/mrp/protobuf/NowPlayingInfo.proto\x1a\x1fpyatv/mrp/protobuf/Common.proto\"\xc1\x03\n\x0eNowPlayingInfo\x12\r\n\x05\x61lbum\x18\x01 \x01(\t\x12\x0e\n\x06\x61rtist\x18\x02 \x01(\t\x12\x10\n\x08\x64uration\x18\x03 \x01(\x01\x12\x13\n\x0b\x65lapsedTime\x18\x04 \x01(\x01\x12\x14\n\x0cplaybackRate\x18\x05 \x01(\x02\x12$\n\nrepeatMode\x18\x06 \x01(\x0e\x32\x10.RepeatMode.Enum\x12&\n\x0bshuffleMode\x18\x07 \x01(\x0e\x32\x11.ShuffleMode.Enum\x12\x11\n\ttimestamp\x18\x08 \x01(\x01\x12\r\n\x05title\x18\t \x01(\t\x12\x18\n\x10uniqueIdentifier\x18\n \x01(\x04\x12\x17\n\x0fisExplicitTrack\x18\x0b \x01(\x08\x12\x12\n\nisMusicApp\x18\x0c \x01(\x08\x12\x1e\n\x16radioStationIdentifier\x18\r \x01(\x03\x12\x18\n\x10radioStationHash\x18\x0e \x01(\t\x12\x18\n\x10radioStationName\x18\x0f \x01(\t\x12\x19\n\x11\x61rtworkDataDigest\x18\x10 \x01(\x0c\x12\x14\n\x0cisAlwaysLive\x18\x11 \x01(\x08\x12\x17\n\x0fisAdvertisement\x18\x12 \x01(\x08'
  ,
  dependencies=[pyatv_dot_mrp_dot_protobuf_dot_Common__pb2.DESCRIPTOR,])




_NOWPLAYINGINFO = _descriptor.Descriptor(
  name='NowPlayingInfo',
  full_name='NowPlayingInfo',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='album', full_name='NowPlayingInfo.album', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='artist', full_name='NowPlayingInfo.artist', index=1,
      number=2, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='duration', full_name='NowPlayingInfo.duration', index=2,
      number=3, type=1, cpp_type=5, label=1,
      has_default_value=False, default_value=float(0),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='elapsedTime', full_name='NowPlayingInfo.elapsedTime', index=3,
      number=4, type=1, cpp_type=5, label=1,
      has_default_value=False, default_value=float(0),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='playbackRate', full_name='NowPlayingInfo.playbackRate', index=4,
      number=5, type=2, cpp_type=6, label=1,
      has_default_value=False, default_value=float(0),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='repeatMode', full_name='NowPlayingInfo.repeatMode', index=5,
      number=6, type=14, cpp_type=8, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='shuffleMode', full_name='NowPlayingInfo.shuffleMode', index=6,
      number=7, type=14, cpp_type=8, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='timestamp', full_name='NowPlayingInfo.timestamp', index=7,
      number=8, type=1, cpp_type=5, label=1,
      has_default_value=False, default_value=float(0),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='title', full_name='NowPlayingInfo.title', index=8,
      number=9, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='uniqueIdentifier', full_name='NowPlayingInfo.uniqueIdentifier', index=9,
      number=10, type=4, cpp_type=4, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='isExplicitTrack', full_name='NowPlayingInfo.isExplicitTrack', index=10,
      number=11, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='isMusicApp', full_name='NowPlayingInfo.isMusicApp', index=11,
      number=12, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='radioStationIdentifier', full_name='NowPlayingInfo.radioStationIdentifier', index=12,
      number=13, type=3, cpp_type=2, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='radioStationHash', full_name='NowPlayingInfo.radioStationHash', index=13,
      number=14, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='radioStationName', full_name='NowPlayingInfo.radioStationName', index=14,
      number=15, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='artworkDataDigest', full_name='NowPlayingInfo.artworkDataDigest', index=15,
      number=16, type=12, cpp_type=9, label=1,
      has_default_value=False, default_value=b"",
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='isAlwaysLive', full_name='NowPlayingInfo.isAlwaysLive', index=16,
      number=17, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='isAdvertisement', full_name='NowPlayingInfo.isAdvertisement', index=17,
      number=18, type=8, cpp_type=7, label=1,
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
  serialized_start=77,
  serialized_end=526,
)

_NOWPLAYINGINFO.fields_by_name['repeatMode'].enum_type = pyatv_dot_mrp_dot_protobuf_dot_Common__pb2._REPEATMODE_ENUM
_NOWPLAYINGINFO.fields_by_name['shuffleMode'].enum_type = pyatv_dot_mrp_dot_protobuf_dot_Common__pb2._SHUFFLEMODE_ENUM
DESCRIPTOR.message_types_by_name['NowPlayingInfo'] = _NOWPLAYINGINFO
_sym_db.RegisterFileDescriptor(DESCRIPTOR)

NowPlayingInfo = _reflection.GeneratedProtocolMessageType('NowPlayingInfo', (_message.Message,), {
  'DESCRIPTOR' : _NOWPLAYINGINFO,
  '__module__' : 'pyatv.mrp.protobuf.NowPlayingInfo_pb2'
  # @@protoc_insertion_point(class_scope:NowPlayingInfo)
  })
_sym_db.RegisterMessage(NowPlayingInfo)


# @@protoc_insertion_point(module_scope)
