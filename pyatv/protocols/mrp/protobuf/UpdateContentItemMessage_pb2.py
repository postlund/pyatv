# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# NO CHECKED-IN PROTOBUF GENCODE
# source: pyatv/protocols/mrp/protobuf/UpdateContentItemMessage.proto
# Protobuf Python Version: 5.28.0
"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import runtime_version as _runtime_version
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
_runtime_version.ValidateProtobufRuntimeVersion(
    _runtime_version.Domain.PUBLIC,
    5,
    28,
    0,
    '',
    'pyatv/protocols/mrp/protobuf/UpdateContentItemMessage.proto'
)
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()


from pyatv.protocols.mrp.protobuf import ProtocolMessage_pb2 as pyatv_dot_protocols_dot_mrp_dot_protobuf_dot_ProtocolMessage__pb2
from pyatv.protocols.mrp.protobuf import ContentItem_pb2 as pyatv_dot_protocols_dot_mrp_dot_protobuf_dot_ContentItem__pb2
from pyatv.protocols.mrp.protobuf import PlayerPath_pb2 as pyatv_dot_protocols_dot_mrp_dot_protobuf_dot_PlayerPath__pb2


DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n;pyatv/protocols/mrp/protobuf/UpdateContentItemMessage.proto\x1a\x32pyatv/protocols/mrp/protobuf/ProtocolMessage.proto\x1a.pyatv/protocols/mrp/protobuf/ContentItem.proto\x1a-pyatv/protocols/mrp/protobuf/PlayerPath.proto\"_\n\x18UpdateContentItemMessage\x12\"\n\x0c\x63ontentItems\x18\x01 \x03(\x0b\x32\x0c.ContentItem\x12\x1f\n\nplayerPath\x18\x02 \x01(\x0b\x32\x0b.PlayerPath:M\n\x18updateContentItemMessage\x12\x10.ProtocolMessage\x18< \x01(\x0b\x32\x19.UpdateContentItemMessage')

_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'pyatv.protocols.mrp.protobuf.UpdateContentItemMessage_pb2', _globals)
if not _descriptor._USE_C_DESCRIPTORS:
  DESCRIPTOR._loaded_options = None
  _globals['_UPDATECONTENTITEMMESSAGE']._serialized_start=210
  _globals['_UPDATECONTENTITEMMESSAGE']._serialized_end=305
# @@protoc_insertion_point(module_scope)
