# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# NO CHECKED-IN PROTOBUF GENCODE
# source: pyatv/protocols/mrp/protobuf/VolumeDidChangeMessage.proto
# Protobuf Python Version: 5.28.1
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
    1,
    '',
    'pyatv/protocols/mrp/protobuf/VolumeDidChangeMessage.proto'
)
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()


from pyatv.protocols.mrp.protobuf import ProtocolMessage_pb2 as pyatv_dot_protocols_dot_mrp_dot_protobuf_dot_ProtocolMessage__pb2


DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n9pyatv/protocols/mrp/protobuf/VolumeDidChangeMessage.proto\x1a\x32pyatv/protocols/mrp/protobuf/ProtocolMessage.proto\"V\n\x16VolumeDidChangeMessage\x12\x0e\n\x06volume\x18\x01 \x01(\x02\x12\x13\n\x0b\x65ndpointUID\x18\x02 \x01(\t\x12\x17\n\x0foutputDeviceUID\x18\x03 \x01(\t:I\n\x16volumeDidChangeMessage\x12\x10.ProtocolMessage\x18\x38 \x01(\x0b\x32\x17.VolumeDidChangeMessage')

_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'pyatv.protocols.mrp.protobuf.VolumeDidChangeMessage_pb2', _globals)
if not _descriptor._USE_C_DESCRIPTORS:
  DESCRIPTOR._loaded_options = None
  _globals['_VOLUMEDIDCHANGEMESSAGE']._serialized_start=113
  _globals['_VOLUMEDIDCHANGEMESSAGE']._serialized_end=199
# @@protoc_insertion_point(module_scope)
