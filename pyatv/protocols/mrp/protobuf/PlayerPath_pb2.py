# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: pyatv/protocols/mrp/protobuf/PlayerPath.proto
"""Generated protocol buffer code."""
from google.protobuf.internal import builder as _builder
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import symbol_database as _symbol_database
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()


from pyatv.protocols.mrp.protobuf import Origin_pb2 as pyatv_dot_protocols_dot_mrp_dot_protobuf_dot_Origin__pb2
from pyatv.protocols.mrp.protobuf import NowPlayingClient_pb2 as pyatv_dot_protocols_dot_mrp_dot_protobuf_dot_NowPlayingClient__pb2
from pyatv.protocols.mrp.protobuf import NowPlayingPlayer_pb2 as pyatv_dot_protocols_dot_mrp_dot_protobuf_dot_NowPlayingPlayer__pb2


DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n-pyatv/protocols/mrp/protobuf/PlayerPath.proto\x1a)pyatv/protocols/mrp/protobuf/Origin.proto\x1a\x33pyatv/protocols/mrp/protobuf/NowPlayingClient.proto\x1a\x33pyatv/protocols/mrp/protobuf/NowPlayingPlayer.proto\"k\n\nPlayerPath\x12\x17\n\x06origin\x18\x01 \x01(\x0b\x32\x07.Origin\x12!\n\x06\x63lient\x18\x02 \x01(\x0b\x32\x11.NowPlayingClient\x12!\n\x06player\x18\x03 \x01(\x0b\x32\x11.NowPlayingPlayer')

_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'pyatv.protocols.mrp.protobuf.PlayerPath_pb2', _globals)
if _descriptor._USE_C_DESCRIPTORS == False:

  DESCRIPTOR._options = None
  _globals['_PLAYERPATH']._serialized_start=198
  _globals['_PLAYERPATH']._serialized_end=305
# @@protoc_insertion_point(module_scope)
