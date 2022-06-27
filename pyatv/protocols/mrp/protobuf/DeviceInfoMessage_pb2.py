# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: pyatv/protocols/mrp/protobuf/DeviceInfoMessage.proto
"""Generated protocol buffer code."""
from google.protobuf.internal import builder as _builder
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import symbol_database as _symbol_database
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()


from pyatv.protocols.mrp.protobuf import ProtocolMessage_pb2 as pyatv_dot_protocols_dot_mrp_dot_protobuf_dot_ProtocolMessage__pb2
from pyatv.protocols.mrp.protobuf import Common_pb2 as pyatv_dot_protocols_dot_mrp_dot_protobuf_dot_Common__pb2


DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n4pyatv/protocols/mrp/protobuf/DeviceInfoMessage.proto\x1a\x32pyatv/protocols/mrp/protobuf/ProtocolMessage.proto\x1a)pyatv/protocols/mrp/protobuf/Common.proto\"\xf2\x08\n\x11\x44\x65viceInfoMessage\x12\x18\n\x10uniqueIdentifier\x18\x01 \x02(\t\x12\x0c\n\x04name\x18\x02 \x02(\t\x12\x1a\n\x12localizedModelName\x18\x03 \x01(\t\x12\x1a\n\x12systemBuildVersion\x18\x04 \x02(\t\x12#\n\x1b\x61pplicationBundleIdentifier\x18\x05 \x02(\t\x12 \n\x18\x61pplicationBundleVersion\x18\x06 \x01(\t\x12\x17\n\x0fprotocolVersion\x18\x07 \x02(\x05\x12 \n\x18lastSupportedMessageType\x18\x08 \x01(\r\x12\x1d\n\x15supportsSystemPairing\x18\t \x01(\x08\x12\x15\n\rallowsPairing\x18\n \x01(\x08\x12\x11\n\tconnected\x18\x0b \x01(\x08\x12\x1e\n\x16systemMediaApplication\x18\x0c \x01(\t\x12\x13\n\x0bsupportsACL\x18\r \x01(\x08\x12\x1b\n\x13supportsSharedQueue\x18\x0e \x01(\x08\x12\x1e\n\x16supportsExtendedMotion\x18\x0f \x01(\x08\x12\x18\n\x10\x62luetoothAddress\x18\x10 \x01(\x0c\x12\x1a\n\x12sharedQueueVersion\x18\x11 \x01(\r\x12\x11\n\tdeviceUID\x18\x13 \x01(\t\x12\x1d\n\x15managedConfigDeviceID\x18\x14 \x01(\t\x12&\n\x0b\x64\x65viceClass\x18\x15 \x01(\x0e\x32\x11.DeviceClass.Enum\x12\x1a\n\x12logicalDeviceCount\x18\x16 \x01(\r\x12\x1a\n\x12tightlySyncedGroup\x18\x17 \x01(\x08\x12\x1a\n\x12isProxyGroupPlayer\x18\x18 \x01(\x08\x12\x14\n\x0ctightSyncUID\x18\x19 \x01(\t\x12\x10\n\x08groupUID\x18\x1a \x01(\t\x12\x11\n\tgroupName\x18\x1b \x01(\t\x12*\n\x0egroupedDevices\x18\x1c \x03(\x0b\x32\x12.DeviceInfoMessage\x12\x15\n\risGroupLeader\x18\x1d \x01(\x08\x12\x17\n\x0fisAirplayActive\x18\x1e \x01(\x08\x12 \n\x18systemPodcastApplication\x18\x1f \x01(\t\x12\x1d\n\x15senderDefaultGroupUID\x18  \x01(\t\x12\x18\n\x10\x61irplayReceivers\x18! \x03(\t\x12\x11\n\tlinkAgent\x18\" \x01(\t\x12\x11\n\tclusterID\x18# \x01(\t\x12\x17\n\x0f\x63lusterLeaderID\x18$ \x01(\t\x12\x13\n\x0b\x63lusterType\x18% \x01(\r\x12\x16\n\x0eisClusterAware\x18& \x01(\x08\x12\x0f\n\x07modelID\x18\' \x01(\t\x12\x1b\n\x13supportsMultiplayer\x18( \x01(\x08\x12\x18\n\x10routingContextID\x18) \x01(\t\x12\x16\n\x0e\x61irPlayGroupID\x18* \x01(\t\x12\x1e\n\x16systemBooksApplication\x18+ \x01(\t:?\n\x11\x64\x65viceInfoMessage\x12\x10.ProtocolMessage\x18\x14 \x01(\x0b\x32\x12.DeviceInfoMessage')

_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, globals())
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'pyatv.protocols.mrp.protobuf.DeviceInfoMessage_pb2', globals())
if _descriptor._USE_C_DESCRIPTORS == False:
  pyatv_dot_protocols_dot_mrp_dot_protobuf_dot_ProtocolMessage__pb2.ProtocolMessage.RegisterExtension(deviceInfoMessage)

  DESCRIPTOR._options = None
  _DEVICEINFOMESSAGE._serialized_start=152
  _DEVICEINFOMESSAGE._serialized_end=1290
# @@protoc_insertion_point(module_scope)
