# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# NO CHECKED-IN PROTOBUF GENCODE
# source: pyatv/protocols/mrp/protobuf/SendPackedVirtualTouchEventMessage.proto
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
    'pyatv/protocols/mrp/protobuf/SendPackedVirtualTouchEventMessage.proto'
)
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()


from pyatv.protocols.mrp.protobuf import ProtocolMessage_pb2 as pyatv_dot_protocols_dot_mrp_dot_protobuf_dot_ProtocolMessage__pb2


DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\nEpyatv/protocols/mrp/protobuf/SendPackedVirtualTouchEventMessage.proto\x1a\x32pyatv/protocols/mrp/protobuf/ProtocolMessage.proto\"{\n\"SendPackedVirtualTouchEventMessage\x12\x0c\n\x04\x64\x61ta\x18\x01 \x01(\x0c\"G\n\x05Phase\x12\t\n\x05\x42\x65gan\x10\x01\x12\t\n\x05Moved\x10\x02\x12\x0e\n\nStationary\x10\x03\x12\t\n\x05\x45nded\x10\x04\x12\r\n\tCancelled\x10\x05:a\n\"sendPackedVirtualTouchEventMessage\x12\x10.ProtocolMessage\x18/ \x01(\x0b\x32#.SendPackedVirtualTouchEventMessage')

_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'pyatv.protocols.mrp.protobuf.SendPackedVirtualTouchEventMessage_pb2', _globals)
if not _descriptor._USE_C_DESCRIPTORS:
  DESCRIPTOR._loaded_options = None
  _globals['_SENDPACKEDVIRTUALTOUCHEVENTMESSAGE']._serialized_start=125
  _globals['_SENDPACKEDVIRTUALTOUCHEVENTMESSAGE']._serialized_end=248
  _globals['_SENDPACKEDVIRTUALTOUCHEVENTMESSAGE_PHASE']._serialized_start=177
  _globals['_SENDPACKEDVIRTUALTOUCHEVENTMESSAGE_PHASE']._serialized_end=248
# @@protoc_insertion_point(module_scope)
