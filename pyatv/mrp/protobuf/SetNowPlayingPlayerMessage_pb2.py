# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: pyatv/mrp/protobuf/SetNowPlayingPlayerMessage.proto

from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()


from pyatv.mrp.protobuf import ProtocolMessage_pb2 as pyatv_dot_mrp_dot_protobuf_dot_ProtocolMessage__pb2
from pyatv.mrp.protobuf import PlayerPath_pb2 as pyatv_dot_mrp_dot_protobuf_dot_PlayerPath__pb2


DESCRIPTOR = _descriptor.FileDescriptor(
  name='pyatv/mrp/protobuf/SetNowPlayingPlayerMessage.proto',
  package='',
  syntax='proto2',
  serialized_options=None,
  serialized_pb=b'\n3pyatv/mrp/protobuf/SetNowPlayingPlayerMessage.proto\x1a(pyatv/mrp/protobuf/ProtocolMessage.proto\x1a#pyatv/mrp/protobuf/PlayerPath.proto\"=\n\x1aSetNowPlayingPlayerMessage\x12\x1f\n\nplayerPath\x18\x01 \x01(\x0b\x32\x0b.PlayerPath:Q\n\x1asetNowPlayingPlayerMessage\x12\x10.ProtocolMessage\x18\x33 \x01(\x0b\x32\x1b.SetNowPlayingPlayerMessage'
  ,
  dependencies=[pyatv_dot_mrp_dot_protobuf_dot_ProtocolMessage__pb2.DESCRIPTOR,pyatv_dot_mrp_dot_protobuf_dot_PlayerPath__pb2.DESCRIPTOR,])


SETNOWPLAYINGPLAYERMESSAGE_FIELD_NUMBER = 51
setNowPlayingPlayerMessage = _descriptor.FieldDescriptor(
  name='setNowPlayingPlayerMessage', full_name='setNowPlayingPlayerMessage', index=0,
  number=51, type=11, cpp_type=10, label=1,
  has_default_value=False, default_value=None,
  message_type=None, enum_type=None, containing_type=None,
  is_extension=True, extension_scope=None,
  serialized_options=None, file=DESCRIPTOR)


_SETNOWPLAYINGPLAYERMESSAGE = _descriptor.Descriptor(
  name='SetNowPlayingPlayerMessage',
  full_name='SetNowPlayingPlayerMessage',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='playerPath', full_name='SetNowPlayingPlayerMessage.playerPath', index=0,
      number=1, type=11, cpp_type=10, label=1,
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
  serialized_start=134,
  serialized_end=195,
)

_SETNOWPLAYINGPLAYERMESSAGE.fields_by_name['playerPath'].message_type = pyatv_dot_mrp_dot_protobuf_dot_PlayerPath__pb2._PLAYERPATH
DESCRIPTOR.message_types_by_name['SetNowPlayingPlayerMessage'] = _SETNOWPLAYINGPLAYERMESSAGE
DESCRIPTOR.extensions_by_name['setNowPlayingPlayerMessage'] = setNowPlayingPlayerMessage
_sym_db.RegisterFileDescriptor(DESCRIPTOR)

SetNowPlayingPlayerMessage = _reflection.GeneratedProtocolMessageType('SetNowPlayingPlayerMessage', (_message.Message,), {
  'DESCRIPTOR' : _SETNOWPLAYINGPLAYERMESSAGE,
  '__module__' : 'pyatv.mrp.protobuf.SetNowPlayingPlayerMessage_pb2'
  # @@protoc_insertion_point(class_scope:SetNowPlayingPlayerMessage)
  })
_sym_db.RegisterMessage(SetNowPlayingPlayerMessage)

setNowPlayingPlayerMessage.message_type = _SETNOWPLAYINGPLAYERMESSAGE
pyatv_dot_mrp_dot_protobuf_dot_ProtocolMessage__pb2.ProtocolMessage.RegisterExtension(setNowPlayingPlayerMessage)

# @@protoc_insertion_point(module_scope)
