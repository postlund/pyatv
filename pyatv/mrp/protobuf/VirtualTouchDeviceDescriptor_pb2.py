# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: pyatv/mrp/protobuf/VirtualTouchDeviceDescriptor.proto

import sys
_b=sys.version_info[0]<3 and (lambda x:x) or (lambda x:x.encode('latin1'))
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database
from google.protobuf import descriptor_pb2
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor.FileDescriptor(
  name='pyatv/mrp/protobuf/VirtualTouchDeviceDescriptor.proto',
  package='',
  syntax='proto2',
  serialized_pb=_b('\n5pyatv/mrp/protobuf/VirtualTouchDeviceDescriptor.proto\"~\n\x1cVirtualTouchDeviceDescriptor\x12\x10\n\x08\x61\x62solute\x18\x01 \x01(\x08\x12\x19\n\x11integratedDisplay\x18\x02 \x01(\x08\x12\x17\n\x0fscreenSizeWidth\x18\x03 \x01(\x02\x12\x18\n\x10screenSizeHeight\x18\x04 \x01(\x02')
)




_VIRTUALTOUCHDEVICEDESCRIPTOR = _descriptor.Descriptor(
  name='VirtualTouchDeviceDescriptor',
  full_name='VirtualTouchDeviceDescriptor',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='absolute', full_name='VirtualTouchDeviceDescriptor.absolute', index=0,
      number=1, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='integratedDisplay', full_name='VirtualTouchDeviceDescriptor.integratedDisplay', index=1,
      number=2, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='screenSizeWidth', full_name='VirtualTouchDeviceDescriptor.screenSizeWidth', index=2,
      number=3, type=2, cpp_type=6, label=1,
      has_default_value=False, default_value=float(0),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='screenSizeHeight', full_name='VirtualTouchDeviceDescriptor.screenSizeHeight', index=3,
      number=4, type=2, cpp_type=6, label=1,
      has_default_value=False, default_value=float(0),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  syntax='proto2',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=57,
  serialized_end=183,
)

DESCRIPTOR.message_types_by_name['VirtualTouchDeviceDescriptor'] = _VIRTUALTOUCHDEVICEDESCRIPTOR
_sym_db.RegisterFileDescriptor(DESCRIPTOR)

VirtualTouchDeviceDescriptor = _reflection.GeneratedProtocolMessageType('VirtualTouchDeviceDescriptor', (_message.Message,), dict(
  DESCRIPTOR = _VIRTUALTOUCHDEVICEDESCRIPTOR,
  __module__ = 'pyatv.mrp.protobuf.VirtualTouchDeviceDescriptor_pb2'
  # @@protoc_insertion_point(class_scope:VirtualTouchDeviceDescriptor)
  ))
_sym_db.RegisterMessage(VirtualTouchDeviceDescriptor)


# @@protoc_insertion_point(module_scope)
