# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: pyatv/protocols/mrp/protobuf/UpdateEndPointsMessage.proto
"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()


from pyatv.protocols.mrp.protobuf import ProtocolMessage_pb2 as pyatv_dot_protocols_dot_mrp_dot_protobuf_dot_ProtocolMessage__pb2


DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n9pyatv/protocols/mrp/protobuf/UpdateEndPointsMessage.proto\x1a\x32pyatv/protocols/mrp/protobuf/ProtocolMessage.proto\"\xc9\x01\n\x14\x41VEndpointDescriptor\x12\x0c\n\x04name\x18\x01 \x01(\t\x12\x18\n\x10uniqueIdentifier\x18\x02 \x01(\t\x12\x17\n\x0fisLocalEndpoint\x18\x05 \x01(\x08\x12\x1a\n\x12instanceIdentifier\x18\x06 \x01(\t\x12\x1a\n\x12isProxyGroupPlayer\x18\x07 \x01(\x08\x12\x16\n\x0e\x63onnectionType\x18\x08 \x01(\x05\x12 \n\x18\x63\x61nModifyGroupMembership\x18\t \x01(\x08\"\\\n\x16UpdateEndPointsMessage\x12(\n\tendpoints\x18\x01 \x01(\x0b\x32\x15.AVEndpointDescriptor\x12\x18\n\x10\x65ndpointFeatures\x18\x02 \x01(\x05:I\n\x16updateEndPointsMessage\x12\x10.ProtocolMessage\x18S \x01(\x0b\x32\x17.UpdateEndPointsMessage')


UPDATEENDPOINTSMESSAGE_FIELD_NUMBER = 83
updateEndPointsMessage = DESCRIPTOR.extensions_by_name['updateEndPointsMessage']

_AVENDPOINTDESCRIPTOR = DESCRIPTOR.message_types_by_name['AVEndpointDescriptor']
_UPDATEENDPOINTSMESSAGE = DESCRIPTOR.message_types_by_name['UpdateEndPointsMessage']
AVEndpointDescriptor = _reflection.GeneratedProtocolMessageType('AVEndpointDescriptor', (_message.Message,), {
  'DESCRIPTOR' : _AVENDPOINTDESCRIPTOR,
  '__module__' : 'pyatv.protocols.mrp.protobuf.UpdateEndPointsMessage_pb2'
  # @@protoc_insertion_point(class_scope:AVEndpointDescriptor)
  })
_sym_db.RegisterMessage(AVEndpointDescriptor)

UpdateEndPointsMessage = _reflection.GeneratedProtocolMessageType('UpdateEndPointsMessage', (_message.Message,), {
  'DESCRIPTOR' : _UPDATEENDPOINTSMESSAGE,
  '__module__' : 'pyatv.protocols.mrp.protobuf.UpdateEndPointsMessage_pb2'
  # @@protoc_insertion_point(class_scope:UpdateEndPointsMessage)
  })
_sym_db.RegisterMessage(UpdateEndPointsMessage)

if _descriptor._USE_C_DESCRIPTORS == False:
  pyatv_dot_protocols_dot_mrp_dot_protobuf_dot_ProtocolMessage__pb2.ProtocolMessage.RegisterExtension(updateEndPointsMessage)

  DESCRIPTOR._options = None
  _AVENDPOINTDESCRIPTOR._serialized_start=114
  _AVENDPOINTDESCRIPTOR._serialized_end=315
  _UPDATEENDPOINTSMESSAGE._serialized_start=317
  _UPDATEENDPOINTSMESSAGE._serialized_end=409
# @@protoc_insertion_point(module_scope)
