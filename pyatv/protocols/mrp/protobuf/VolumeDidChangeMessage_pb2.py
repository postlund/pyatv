# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: pyatv/protocols/mrp/protobuf/VolumeDidChangeMessage.proto
"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()


from pyatv.protocols.mrp.protobuf import ProtocolMessage_pb2 as pyatv_dot_protocols_dot_mrp_dot_protobuf_dot_ProtocolMessage__pb2


DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n9pyatv/protocols/mrp/protobuf/VolumeDidChangeMessage.proto\x1a\x32pyatv/protocols/mrp/protobuf/ProtocolMessage.proto\"V\n\x16VolumeDidChangeMessage\x12\x0e\n\x06volume\x18\x01 \x01(\x02\x12\x13\n\x0b\x65ndpointUID\x18\x02 \x01(\t\x12\x17\n\x0foutputDeviceUID\x18\x03 \x01(\t:I\n\x16volumeDidChangeMessage\x12\x10.ProtocolMessage\x18\x38 \x01(\x0b\x32\x17.VolumeDidChangeMessage')


VOLUMEDIDCHANGEMESSAGE_FIELD_NUMBER = 56
volumeDidChangeMessage = DESCRIPTOR.extensions_by_name['volumeDidChangeMessage']

_VOLUMEDIDCHANGEMESSAGE = DESCRIPTOR.message_types_by_name['VolumeDidChangeMessage']
VolumeDidChangeMessage = _reflection.GeneratedProtocolMessageType('VolumeDidChangeMessage', (_message.Message,), {
  'DESCRIPTOR' : _VOLUMEDIDCHANGEMESSAGE,
  '__module__' : 'pyatv.protocols.mrp.protobuf.VolumeDidChangeMessage_pb2'
  # @@protoc_insertion_point(class_scope:VolumeDidChangeMessage)
  })
_sym_db.RegisterMessage(VolumeDidChangeMessage)

if _descriptor._USE_C_DESCRIPTORS == False:
  pyatv_dot_protocols_dot_mrp_dot_protobuf_dot_ProtocolMessage__pb2.ProtocolMessage.RegisterExtension(volumeDidChangeMessage)

  DESCRIPTOR._options = None
  _VOLUMEDIDCHANGEMESSAGE._serialized_start=113
  _VOLUMEDIDCHANGEMESSAGE._serialized_end=199
# @@protoc_insertion_point(module_scope)
