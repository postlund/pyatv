# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: pyatv/protocols/mrp/protobuf/VoiceInputDeviceDescriptorMessage.proto
"""Generated protocol buffer code."""
from google.protobuf.internal import builder as _builder
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import symbol_database as _symbol_database
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()


from pyatv.protocols.mrp.protobuf import AudioFormatSettingsMessage_pb2 as pyatv_dot_protocols_dot_mrp_dot_protobuf_dot_AudioFormatSettingsMessage__pb2


DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\nDpyatv/protocols/mrp/protobuf/VoiceInputDeviceDescriptorMessage.proto\x1a=pyatv/protocols/mrp/protobuf/AudioFormatSettingsMessage.proto\"y\n\x1aVoiceInputDeviceDescriptor\x12+\n\rdefaultFormat\x18\x01 \x01(\x0b\x32\x14.AudioFormatSettings\x12.\n\x10supportedFormats\x18\x02 \x03(\x0b\x32\x14.AudioFormatSettings')

_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, globals())
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'pyatv.protocols.mrp.protobuf.VoiceInputDeviceDescriptorMessage_pb2', globals())
if _descriptor._USE_C_DESCRIPTORS == False:

  DESCRIPTOR._options = None
  _VOICEINPUTDEVICEDESCRIPTOR._serialized_start=135
  _VOICEINPUTDEVICEDESCRIPTOR._serialized_end=256
# @@protoc_insertion_point(module_scope)
