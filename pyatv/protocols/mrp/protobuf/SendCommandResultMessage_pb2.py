# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: pyatv/protocols/mrp/protobuf/SendCommandResultMessage.proto
"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()


from pyatv.protocols.mrp.protobuf import ProtocolMessage_pb2 as pyatv_dot_protocols_dot_mrp_dot_protobuf_dot_ProtocolMessage__pb2
from pyatv.protocols.mrp.protobuf import PlayerPath_pb2 as pyatv_dot_protocols_dot_mrp_dot_protobuf_dot_PlayerPath__pb2


DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n;pyatv/protocols/mrp/protobuf/SendCommandResultMessage.proto\x1a\x32pyatv/protocols/mrp/protobuf/ProtocolMessage.proto\x1a-pyatv/protocols/mrp/protobuf/PlayerPath.proto\"\xfc\x01\n\tSendError\"\xee\x01\n\x04\x45num\x12\x0b\n\x07NoError\x10\x00\x12\x17\n\x13\x41pplicationNotFound\x10\x01\x12\x14\n\x10\x43onnectionFailed\x10\x02\x12\x0b\n\x07Ignored\x10\x03\x12\x1d\n\x19\x43ouldNotLaunchApplication\x10\x04\x12\x0c\n\x08TimedOut\x10\x05\x12\x16\n\x12OriginDoesNotExist\x10\x06\x12\x12\n\x0eInvalidOptions\x10\x07\x12\x15\n\x11NoCommandHandlers\x10\x08\x12\x1b\n\x17\x41pplicationNotInstalled\x10\t\x12\x10\n\x0cNotSupported\x10\n\"\xf3\x03\n\x13HandlerReturnStatus\"\xdb\x03\n\x04\x45num\x12\x0b\n\x07Success\x10\x00\x12\x11\n\rNoSuchContent\x10\x01\x12\x11\n\rCommandFailed\x10\x02\x12\x1e\n\x1aNoActionableNowPlayingItem\x10\n\x12\x12\n\x0e\x44\x65viceNotFound\x10\x14\x12\x0f\n\x0bUIKitLegacy\x10\x03\x12\x14\n\x10SkipAdProhibited\x10\x64\x12\x16\n\x12QueueIsUserCurated\x10\x65\x12\x1d\n\x19UserModifiedQueueDisabled\x10\x66\x12\x33\n/UserQueueModificationNotSupportedForCurrentItem\x10g\x12&\n\"SubscriptionRequiredForSharedQueue\x10h\x12!\n\x1dInsertionPositionNotSpecified\x10i\x12\x1c\n\x18InvalidInsertionPosition\x10j\x12 \n\x1cRequestParametersOutOfBounds\x10k\x12\x14\n\x10SkipLimitReached\x10l\x12\x1a\n\x15\x41uthenticationFailure\x10\x91\x03\x12\x1c\n\x17MediaServiceUnavailable\x10\xf5\x03\"\xf5\x03\n\x15SendCommandStatusCode\"\xdb\x03\n\x04\x45num\x12\x0b\n\x07Success\x10\x00\x12\x11\n\rNoSuchContent\x10\x01\x12\x11\n\rCommandFailed\x10\x02\x12\x1e\n\x1aNoActionableNowPlayingItem\x10\n\x12\x12\n\x0e\x44\x65viceNotFound\x10\x14\x12\x0f\n\x0bUIKitLegacy\x10\x03\x12\x14\n\x10SkipAdProhibited\x10\x64\x12\x16\n\x12QueueIsUserCurated\x10\x65\x12\x1d\n\x19UserModifiedQueueDisabled\x10\x66\x12\x33\n/UserQueueModificationNotSupportedForCurrentItem\x10g\x12&\n\"SubscriptionRequiredForSharedQueue\x10h\x12!\n\x1dInsertionPositionNotSpecified\x10i\x12\x1c\n\x18InvalidInsertionPosition\x10j\x12 \n\x1cRequestParametersOutOfBounds\x10k\x12\x14\n\x10SkipLimitReached\x10l\x12\x1a\n\x15\x41uthenticationFailure\x10\x91\x03\x12\x1c\n\x17MediaServiceUnavailable\x10\xf5\x03\"C\n\x15SendCommandResultType\"*\n\x04\x45num\x12\n\n\x06\x44ialog\x10\x01\x12\t\n\x05\x45rror\x10\x02\x12\x0b\n\x06\x43ustom\x10\xe7\x07\"\xa1\x01\n\x17SendCommandResultStatus\x12/\n\nstatusCode\x18\x01 \x01(\x0e\x32\x1b.SendCommandStatusCode.Enum\x12)\n\x04type\x18\x02 \x01(\x0e\x32\x1b.SendCommandResultType.Enum\x12\x12\n\ncustomData\x18\x05 \x01(\x0c\x12\x16\n\x0e\x63ustomDataType\x18\x06 \x01(\t\"\x84\x01\n\x11SendCommandResult\x12\x1f\n\nplayerPath\x18\x01 \x01(\x0b\x32\x0b.PlayerPath\x12\"\n\tsendError\x18\x02 \x01(\x0e\x32\x0f.SendError.Enum\x12*\n\x08statuses\x18\x03 \x03(\x0b\x32\x18.SendCommandResultStatus\"\xf7\x01\n\x18SendCommandResultMessage\x12\"\n\tsendError\x18\x01 \x01(\x0e\x32\x0f.SendError.Enum\x12\x36\n\x13handlerReturnStatus\x18\x02 \x01(\x0e\x32\x19.HandlerReturnStatus.Enum\x12 \n\x18handlerReturnStatusDatas\x18\x03 \x03(\x0c\x12\x11\n\tcommandID\x18\x04 \x01(\t\x12\x1f\n\nplayerPath\x18\x05 \x01(\x0b\x32\x0b.PlayerPath\x12)\n\rcommandResult\x18\x06 \x01(\x0b\x32\x12.SendCommandResult:M\n\x18sendCommandResultMessage\x12\x10.ProtocolMessage\x18\x07 \x01(\x0b\x32\x19.SendCommandResultMessage')


SENDCOMMANDRESULTMESSAGE_FIELD_NUMBER = 7
sendCommandResultMessage = DESCRIPTOR.extensions_by_name['sendCommandResultMessage']

_SENDERROR = DESCRIPTOR.message_types_by_name['SendError']
_HANDLERRETURNSTATUS = DESCRIPTOR.message_types_by_name['HandlerReturnStatus']
_SENDCOMMANDSTATUSCODE = DESCRIPTOR.message_types_by_name['SendCommandStatusCode']
_SENDCOMMANDRESULTTYPE = DESCRIPTOR.message_types_by_name['SendCommandResultType']
_SENDCOMMANDRESULTSTATUS = DESCRIPTOR.message_types_by_name['SendCommandResultStatus']
_SENDCOMMANDRESULT = DESCRIPTOR.message_types_by_name['SendCommandResult']
_SENDCOMMANDRESULTMESSAGE = DESCRIPTOR.message_types_by_name['SendCommandResultMessage']
_SENDERROR_ENUM = _SENDERROR.enum_types_by_name['Enum']
_HANDLERRETURNSTATUS_ENUM = _HANDLERRETURNSTATUS.enum_types_by_name['Enum']
_SENDCOMMANDSTATUSCODE_ENUM = _SENDCOMMANDSTATUSCODE.enum_types_by_name['Enum']
_SENDCOMMANDRESULTTYPE_ENUM = _SENDCOMMANDRESULTTYPE.enum_types_by_name['Enum']
SendError = _reflection.GeneratedProtocolMessageType('SendError', (_message.Message,), {
  'DESCRIPTOR' : _SENDERROR,
  '__module__' : 'pyatv.protocols.mrp.protobuf.SendCommandResultMessage_pb2'
  # @@protoc_insertion_point(class_scope:SendError)
  })
_sym_db.RegisterMessage(SendError)

HandlerReturnStatus = _reflection.GeneratedProtocolMessageType('HandlerReturnStatus', (_message.Message,), {
  'DESCRIPTOR' : _HANDLERRETURNSTATUS,
  '__module__' : 'pyatv.protocols.mrp.protobuf.SendCommandResultMessage_pb2'
  # @@protoc_insertion_point(class_scope:HandlerReturnStatus)
  })
_sym_db.RegisterMessage(HandlerReturnStatus)

SendCommandStatusCode = _reflection.GeneratedProtocolMessageType('SendCommandStatusCode', (_message.Message,), {
  'DESCRIPTOR' : _SENDCOMMANDSTATUSCODE,
  '__module__' : 'pyatv.protocols.mrp.protobuf.SendCommandResultMessage_pb2'
  # @@protoc_insertion_point(class_scope:SendCommandStatusCode)
  })
_sym_db.RegisterMessage(SendCommandStatusCode)

SendCommandResultType = _reflection.GeneratedProtocolMessageType('SendCommandResultType', (_message.Message,), {
  'DESCRIPTOR' : _SENDCOMMANDRESULTTYPE,
  '__module__' : 'pyatv.protocols.mrp.protobuf.SendCommandResultMessage_pb2'
  # @@protoc_insertion_point(class_scope:SendCommandResultType)
  })
_sym_db.RegisterMessage(SendCommandResultType)

SendCommandResultStatus = _reflection.GeneratedProtocolMessageType('SendCommandResultStatus', (_message.Message,), {
  'DESCRIPTOR' : _SENDCOMMANDRESULTSTATUS,
  '__module__' : 'pyatv.protocols.mrp.protobuf.SendCommandResultMessage_pb2'
  # @@protoc_insertion_point(class_scope:SendCommandResultStatus)
  })
_sym_db.RegisterMessage(SendCommandResultStatus)

SendCommandResult = _reflection.GeneratedProtocolMessageType('SendCommandResult', (_message.Message,), {
  'DESCRIPTOR' : _SENDCOMMANDRESULT,
  '__module__' : 'pyatv.protocols.mrp.protobuf.SendCommandResultMessage_pb2'
  # @@protoc_insertion_point(class_scope:SendCommandResult)
  })
_sym_db.RegisterMessage(SendCommandResult)

SendCommandResultMessage = _reflection.GeneratedProtocolMessageType('SendCommandResultMessage', (_message.Message,), {
  'DESCRIPTOR' : _SENDCOMMANDRESULTMESSAGE,
  '__module__' : 'pyatv.protocols.mrp.protobuf.SendCommandResultMessage_pb2'
  # @@protoc_insertion_point(class_scope:SendCommandResultMessage)
  })
_sym_db.RegisterMessage(SendCommandResultMessage)

if _descriptor._USE_C_DESCRIPTORS == False:
  pyatv_dot_protocols_dot_mrp_dot_protobuf_dot_ProtocolMessage__pb2.ProtocolMessage.RegisterExtension(sendCommandResultMessage)

  DESCRIPTOR._options = None
  _SENDERROR._serialized_start=163
  _SENDERROR._serialized_end=415
  _SENDERROR_ENUM._serialized_start=177
  _SENDERROR_ENUM._serialized_end=415
  _HANDLERRETURNSTATUS._serialized_start=418
  _HANDLERRETURNSTATUS._serialized_end=917
  _HANDLERRETURNSTATUS_ENUM._serialized_start=442
  _HANDLERRETURNSTATUS_ENUM._serialized_end=917
  _SENDCOMMANDSTATUSCODE._serialized_start=920
  _SENDCOMMANDSTATUSCODE._serialized_end=1421
  _SENDCOMMANDSTATUSCODE_ENUM._serialized_start=442
  _SENDCOMMANDSTATUSCODE_ENUM._serialized_end=917
  _SENDCOMMANDRESULTTYPE._serialized_start=1423
  _SENDCOMMANDRESULTTYPE._serialized_end=1490
  _SENDCOMMANDRESULTTYPE_ENUM._serialized_start=1448
  _SENDCOMMANDRESULTTYPE_ENUM._serialized_end=1490
  _SENDCOMMANDRESULTSTATUS._serialized_start=1493
  _SENDCOMMANDRESULTSTATUS._serialized_end=1654
  _SENDCOMMANDRESULT._serialized_start=1657
  _SENDCOMMANDRESULT._serialized_end=1789
  _SENDCOMMANDRESULTMESSAGE._serialized_start=1792
  _SENDCOMMANDRESULTMESSAGE._serialized_end=2039
# @@protoc_insertion_point(module_scope)
