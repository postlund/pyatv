# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: pyatv/protocols/mrp/protobuf/SendCommandMessage.proto
"""Generated protocol buffer code."""
from google.protobuf.internal import builder as _builder
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import symbol_database as _symbol_database
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()


from pyatv.protocols.mrp.protobuf import ProtocolMessage_pb2 as pyatv_dot_protocols_dot_mrp_dot_protobuf_dot_ProtocolMessage__pb2
from pyatv.protocols.mrp.protobuf import CommandInfo_pb2 as pyatv_dot_protocols_dot_mrp_dot_protobuf_dot_CommandInfo__pb2
from pyatv.protocols.mrp.protobuf import CommandOptions_pb2 as pyatv_dot_protocols_dot_mrp_dot_protobuf_dot_CommandOptions__pb2
from pyatv.protocols.mrp.protobuf import PlayerPath_pb2 as pyatv_dot_protocols_dot_mrp_dot_protobuf_dot_PlayerPath__pb2


DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n5pyatv/protocols/mrp/protobuf/SendCommandMessage.proto\x1a\x32pyatv/protocols/mrp/protobuf/ProtocolMessage.proto\x1a.pyatv/protocols/mrp/protobuf/CommandInfo.proto\x1a\x31pyatv/protocols/mrp/protobuf/CommandOptions.proto\x1a-pyatv/protocols/mrp/protobuf/PlayerPath.proto\"r\n\x12SendCommandMessage\x12\x19\n\x07\x63ommand\x18\x01 \x01(\x0e\x32\x08.Command\x12 \n\x07options\x18\x02 \x01(\x0b\x32\x0f.CommandOptions\x12\x1f\n\nplayerPath\x18\x03 \x01(\x0b\x32\x0b.PlayerPath:A\n\x12sendCommandMessage\x12\x10.ProtocolMessage\x18\x06 \x01(\x0b\x32\x13.SendCommandMessage')

_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'pyatv.protocols.mrp.protobuf.SendCommandMessage_pb2', _globals)
if _descriptor._USE_C_DESCRIPTORS == False:
  pyatv_dot_protocols_dot_mrp_dot_protobuf_dot_ProtocolMessage__pb2.ProtocolMessage.RegisterExtension(sendCommandMessage)

  DESCRIPTOR._options = None
  _globals['_SENDCOMMANDMESSAGE']._serialized_start=255
  _globals['_SENDCOMMANDMESSAGE']._serialized_end=369
# @@protoc_insertion_point(module_scope)
