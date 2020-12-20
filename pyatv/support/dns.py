"""Processing functions for raw DNS messages."""
import enum
import io
import logging
import struct
import typing
from ipaddress import IPv4Address

from pyatv.support.collections import CaseInsensitiveDict


_LOGGER = logging.getLogger(__name__)


def unpack_stream(fmt: str, buffer: typing.BinaryIO) -> typing.Tuple:
    """Unpack a tuple from a binary stream, much like `struct.unpack`."""
    size = struct.calcsize(fmt)
    return struct.unpack(fmt, buffer.read(size))


def qname_encode(name: str) -> bytes:
    """Encode QNAME without using name compression."""
    encoded = bytearray()
    for label in name.split("."):
        encoded_label = label.encode("idna")
        encoded_length = len(encoded_label)
        # Length of the encoded label, in bytes, but a maximum of 63
        # The maximum is 63 as the upper two bits are used as a flag for name
        # compression.
        encoded.append(min(encoded_length, 63))
        # TODO: Should an error be raised if a label is too long?
        if encoded_length > 63:
            encoded.extend(encoded_label[:64])
        else:
            encoded.extend(encoded_label)
    # The final component for the root namespace
    encoded.append(0x0)
    return encoded


def parse_string(buffer: typing.BinaryIO) -> bytes:
    """Unpack a DNS character string.

    These are simply a single length byte, followed by up to that many bytes of data.

    This is distinct from "domain-name" encoding; use `parse_domain_name` for that.
    """
    chunk_length = unpack_stream(">B", buffer)[0]
    return buffer.read(chunk_length)


def parse_domain_name(buffer: typing.BinaryIO) -> str:
    """Unpack a domain name, handling any name compression encountered.

    Basically, each component of a domain name (called a "label") is prefixed with a
    length followed by the IDNA encoded label. The final component has a zero length
    with a null label for the DNS root. The tricky part is that labels are limited to 63
    bytes, and the upper two bits of the length are used as a flag for "name
    compression". For full details, see RFC1035, sections 3.1 and 4.1.4.

    This is distinct from "character-string" encoding; use `parse_string` for that.
    """
    labels = []
    compression_offset = None
    while buffer:
        length = unpack_stream(">B", buffer)[0]
        if length == 0:
            break
        # The two high bits of the length are a flag for DNS name compression
        length_flags = (length & 0xC0) >> 6
        # The 10 and 01 flags are reserved
        assert length_flags in (0, 0b11)
        if length_flags == 0b11:
            # Mask off the upper two bits, then concatenate the next byte from the
            # stream to get the offset.
            high_bits: int = length & 0x3F
            new_offset_data = bytearray(buffer.read(1))
            new_offset_data.insert(0, high_bits)
            new_offset = struct.unpack(">H", new_offset_data)[0]
            # I think it's technically possible to have multiple levels of name
            # compression, so make sure we don't lose the original place we need to go
            # back to.
            if compression_offset is None:
                compression_offset = buffer.tell()
            buffer.seek(new_offset)
        elif length_flags == 0:
            label = buffer.read(length)
            labels.append(label)
    if compression_offset is not None:
        buffer.seek(compression_offset)
    return ".".join(label.decode("idna") for label in labels)


def parse_txt_dict(buffer: typing.BinaryIO, length: int) -> typing.Dict[str, bytes]:
    """Parse DNS-SD TXT records into a `dict`."""
    output = CaseInsensitiveDict()
    stop_position = buffer.tell() + length
    while buffer.tell() < stop_position:
        chunk = parse_string(buffer)
        if b"=" not in chunk:
            decoded_chunk = chunk.decode("ascii")
            # missing "=" means its a boolean attribute
            output[decoded_chunk] = True
        else:
            key, value = chunk.split(b"=", 1)
            if not key:
                # Missing keys are skipped
                continue
            try:
                # Keys are explicitly ASCII only
                decoded_key = key.decode("ascii")
            except UnicodeDecodeError:
                _LOGGER.debug("Non-ASCII DNS-SD key encountered: %s", key)
                continue
            # Compared to the keys (ASCII strings), values are opaque binary blobs
            output[decoded_key] = value
    return output


def parse_srv_dict(buffer: typing.BinaryIO):
    """Parse DNS SRV record."""
    priority, weight, port = unpack_stream(">3H", buffer)
    # Name compression isn't allowed by the RFC, but let's accept it anyways
    target = parse_domain_name(buffer)
    # TODO: Should there be a check for target == ".", for marking services that
    # (according to the RFC), "the service is decidedly not available at this domain."
    return {
        "priority": priority,
        "weight": weight,
        "port": port,
        "target": target,
    }


class QueryType(enum.IntEnum):
    """A DNS type ID."""

    A = 0x01
    PTR = 0x0C
    TXT = 0x10
    SRV = 0x21
    ANY = 0xFF

    def parse_rdata(self, buffer: typing.BinaryIO, length: int) -> typing.Any:
        """Parse the RDATA from DNS resource record according to the type of the record.

        If the record type isn't specifically handled, the raw binary data is returned.
        """
        if self is self.A:
            if length != 4:
                raise ValueError(
                    f"An A record must have exactly 4 bytes of data (not {length})"
                )
            return str(IPv4Address(buffer.read(length)))
        elif self is self.PTR:
            return parse_domain_name(buffer)
        elif self is self.TXT:
            return parse_txt_dict(buffer, length)
        elif self is self.SRV:
            return parse_srv_dict(buffer)
        else:
            return buffer.read(length)


class DnsHeader(typing.NamedTuple):
    """Represents the header to a DNS message."""

    id: int
    flags: int
    qdcount: int
    ancount: int
    nscount: int
    arcount: int

    @classmethod
    # Py3.7 allows the quotes to be removes as long as `annotations` is imported from
    # __future__. Py3.10 makes the behavior default.
    def unpack_read(cls, buffer: typing.BinaryIO) -> "DnsHeader":
        """Create a `DnsHeader` from a data stream.

        Only as much data as is needed to create the header is read from the stream,
        leaving it prepped to start parsing questions or resource records immediately
        afterwards.
        """
        return cls._make(unpack_stream(">6H", buffer))

    def pack(self) -> bytes:
        """Generate the packed DNS header data."""
        return struct.pack(">6H", *self)  # pylint: disable=not-an-iterable


class DnsQuestion(typing.NamedTuple):
    """Represents a DNS query."""

    qname: str
    qtype: QueryType
    qclass: int

    @classmethod
    def unpack_read(cls, buffer: typing.BinaryIO) -> "DnsQuestion":
        """Create a `DnsQuestion` from a data stream.

        The entire question data is read from the stream, leaving it ready to parse
        further questions form it, or to parse resource records out of it (depending on
        the DNS message structure).
        """
        qname = parse_domain_name(buffer)
        return cls(qname, *unpack_stream(">2H", buffer))

    def pack(self) -> bytes:
        """Encode the question data as needed for a DNS query or response."""
        data = bytearray(qname_encode(self.qname))
        data.extend(struct.pack(">2H", *self))  # pylint: disable=not-an-iterable
        return data


class DnsResource(typing.NamedTuple):
    """Represents a DNS resource record."""

    qname: str
    qtype: QueryType
    qclass: int
    ttl: int
    rd_length: int
    rd: typing.Any

    @classmethod
    def unpack_read(cls, buffer: typing.BinaryIO) -> "DnsResource":
        """Create a `DnsResource` from data in a data stream.

        All data from a resource record is consumed, leaving the stream ready to be used
        in another call to this method (as needed).
        """
        qname = parse_domain_name(buffer)
        qtype, qclass, ttl, rd_length = unpack_stream(">2HIH", buffer)
        before_rd = buffer.tell()
        if qtype in QueryType.__members__.values():
            qtype = QueryType(qtype)
            rd = qtype.parse_rdata(buffer, rd_length)
        else:
            rd = buffer.read(rd_length)
        assert buffer.tell() == before_rd + rd_length
        return cls(qname, qtype, qclass, ttl, rd_length, rd)


class DnsMessage:
    """Represent a DNS message."""

    def __init__(self, msg_id=0, flags=0x0120):
        """Initialize a new DnsMessage."""
        self.msg_id = msg_id
        self.flags = flags
        self.questions: typing.List[DnsQuestion] = []
        self.answers: typing.List[DnsResource] = []
        self.authorities: typing.List[DnsResource] = []
        self.resources: typing.List[DnsResource] = []

    def unpack(self, msg: bytes):
        """Unpack bytes into a DnsMessage."""
        buffer = io.BytesIO(msg)

        header = DnsHeader.unpack_read(buffer)
        self.msg_id = header.id
        self.flags = header.flags

        # Unpack questions
        self.questions.extend(
            DnsQuestion.unpack_read(buffer) for _ in range((header.qdcount))
        )

        # Unpack answers
        self.answers.extend(
            DnsResource.unpack_read(buffer) for _ in range((header.ancount))
        )

        # Unpack authorities
        self.authorities.extend(
            DnsResource.unpack_read(buffer) for _ in range((header.nscount))
        )

        # Unpack additional resources
        self.resources.extend(
            DnsResource.unpack_read(buffer) for _ in range((header.arcount))
        )

        return self

    def pack(self):
        """Pack message into bytes."""
        header = DnsHeader(
            self.msg_id,
            self.flags,
            len(self.questions),
            len(self.answers),
            len(self.authorities),
            len(self.resources),
        )

        buf = struct.pack(">6H", *header)

        for question in self.questions:
            buf += qname_encode(question.qname)
            buf += struct.pack(">H", question.qtype)
            buf += struct.pack(">H", question.qclass)

        for answer in self.answers:
            data = qname_encode(answer.rd)
            buf += qname_encode(answer.qname)
            buf += struct.pack(">H", answer.qtype)
            buf += struct.pack(">H", answer.qclass)
            buf += struct.pack(">I", answer.ttl)
            buf += struct.pack(">H", len(data))
            buf += data

        for section in [self.authorities, self.resources]:
            for resource in section:
                buf += qname_encode(resource.qname)
                buf += struct.pack(">H", resource.qtype)
                buf += struct.pack(">H", resource.qclass)
                buf += struct.pack(">I", resource.ttl)
                buf += struct.pack(">H", len(resource.rd))
                buf += resource.rd

        return buf

    def __str__(self):
        """Return string representation of DnsMessage."""
        return (
            "MsgId=0x{0:04X}\nFlags=0x{1:04X}\nQuestions={2}\n"
            "Answers={3}\nAuthorities={4}\nResources={5}".format(
                self.msg_id,
                self.flags,
                self.questions,
                self.answers,
                self.authorities,
                self.resources,
            )
        )
