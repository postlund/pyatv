"""Packet formats used by RAOP."""
from pyatv.support.packet import defpacket

RtpHeader = defpacket("RtpHeader", proto="B", type="B", seqno="H")

TimingPacket = RtpHeader.extend(
    "TimingPacket",
    padding="I",
    reftime_sec="I",
    reftime_frac="I",
    recvtime_sec="I",
    recvtime_frac="I",
    sendtime_sec="I",
    sendtime_frac="I",
)

SyncPacket = RtpHeader.extend(
    "SyncPacket",
    now_without_latency="I",
    last_sync_sec="I",
    last_sync_frac="I",
    now="I",
)

# NB: Audio payload is not included here, shall be appended manually
AudioPacketHeader = RtpHeader.extend(
    "AudioPacketHeader",
    timestamp="I",
    ssrc="I",
)

RetransmitReqeust = RtpHeader.extend(
    "RetransmitPacket", lost_seqno="H", lost_packets="H"
)
