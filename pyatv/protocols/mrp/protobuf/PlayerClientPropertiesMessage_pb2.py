# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# NO CHECKED-IN PROTOBUF GENCODE
# source: pyatv/protocols/mrp/protobuf/PlayerClientPropertiesMessage.proto
# Protobuf Python Version: 6.30.2
"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import runtime_version as _runtime_version
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
_runtime_version.ValidateProtobufRuntimeVersion(
    _runtime_version.Domain.PUBLIC,
    6,
    30,
    2,
    '',
    'pyatv/protocols/mrp/protobuf/PlayerClientPropertiesMessage.proto'
)
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()


from pyatv.protocols.mrp.protobuf import ProtocolMessage_pb2 as pyatv_dot_protocols_dot_mrp_dot_protobuf_dot_ProtocolMessage__pb2
from pyatv.protocols.mrp.protobuf import PlayerPath_pb2 as pyatv_dot_protocols_dot_mrp_dot_protobuf_dot_PlayerPath__pb2


DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n@pyatv/protocols/mrp/protobuf/PlayerClientPropertiesMessage.proto\x1a\x32pyatv/protocols/mrp/protobuf/ProtocolMessage.proto\x1a-pyatv/protocols/mrp/protobuf/PlayerPath.proto\"^\n\x1dPlayerClientPropertiesMessage\x12\x1f\n\nplayerPath\x18\x01 \x01(\x0b\x32\x0b.PlayerPath\x12\x1c\n\x14lastPlayingTimestamp\x18\x02 \x01(\x01:W\n\x1dplayerClientPropertiesMessage\x12\x10.ProtocolMessage\x18V \x01(\x0b\x32\x1e.PlayerClientPropertiesMessage')

_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'pyatv.protocols.mrp.protobuf.PlayerClientPropertiesMessage_pb2', _globals)
if not _descriptor._USE_C_DESCRIPTORS:
  DESCRIPTOR._loaded_options = None
  _globals['_PLAYERCLIENTPROPERTIESMESSAGE']._serialized_start=167
  _globals['_PLAYERCLIENTPROPERTIESMESSAGE']._serialized_end=261
# @@protoc_insertion_point(module_scope)
