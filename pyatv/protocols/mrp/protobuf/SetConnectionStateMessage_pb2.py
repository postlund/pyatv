# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# NO CHECKED-IN PROTOBUF GENCODE
# source: pyatv/protocols/mrp/protobuf/SetConnectionStateMessage.proto
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
    'pyatv/protocols/mrp/protobuf/SetConnectionStateMessage.proto'
)
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()


from pyatv.protocols.mrp.protobuf import ProtocolMessage_pb2 as pyatv_dot_protocols_dot_mrp_dot_protobuf_dot_ProtocolMessage__pb2


DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n<pyatv/protocols/mrp/protobuf/SetConnectionStateMessage.proto\x1a\x32pyatv/protocols/mrp/protobuf/ProtocolMessage.proto\"\xa4\x01\n\x19SetConnectionStateMessage\x12\x39\n\x05state\x18\x01 \x01(\x0e\x32*.SetConnectionStateMessage.ConnectionState\"L\n\x0f\x43onnectionState\x12\x08\n\x04None\x10\x00\x12\x0e\n\nConnecting\x10\x01\x12\r\n\tConnected\x10\x02\x12\x10\n\x0c\x44isconnected\x10\x03:O\n\x19setConnectionStateMessage\x12\x10.ProtocolMessage\x18* \x01(\x0b\x32\x1a.SetConnectionStateMessage')

_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'pyatv.protocols.mrp.protobuf.SetConnectionStateMessage_pb2', _globals)
if not _descriptor._USE_C_DESCRIPTORS:
  DESCRIPTOR._loaded_options = None
  _globals['_SETCONNECTIONSTATEMESSAGE']._serialized_start=117
  _globals['_SETCONNECTIONSTATEMESSAGE']._serialized_end=281
  _globals['_SETCONNECTIONSTATEMESSAGE_CONNECTIONSTATE']._serialized_start=205
  _globals['_SETCONNECTIONSTATEMESSAGE_CONNECTIONSTATE']._serialized_end=281
# @@protoc_insertion_point(module_scope)
