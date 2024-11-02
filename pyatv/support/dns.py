"""Processing functions for raw DNS messages."""

import collections.abc
import enum
import io
from ipaddress import IPv4Address
import logging
import struct
import typing
import unicodedata

from zeroconf import ServiceInfo

from pyatv.support.collections import CaseInsensitiveDict

_LOGGER = logging.getLogger(__name__)


def unpack_stream(fmt: str, buffer: typing.BinaryIO) -> typing.Tuple:
    """Unpack data from a binary stream according to the given format string.

    This is basically `struct.unpack`, but for binary streams.
    """
    size = struct.calcsize(fmt)
    return struct.unpack(fmt, buffer.read(size))


class ServiceInstanceName(typing.NamedTuple):
    """Represents either a service or service instance name in the DNS.

    The special thing this class can do is (attempt) to handle periods in the instance
    name correctly.
    """

    instance: typing.Optional[str]
    service: str
    domain: str = "local"

    def __str__(self):
        """Join all components together with periods."""
        return ".".join(typing.cast(typing.Iterable[str], filter(None, self)))

    @classmethod
    def split_name(cls, name: str) -> "ServiceInstanceName":
        """Split a name into instance (optional), service, and domain parts.

        If the name given isn't a service name or service instance name, this method
        raise a `ValueError`.
        """
        labels = name.split(".")
        if len(labels) < 2:
            raise ValueError("There must be at least three labels in a service name")
        for index in range(len(labels) - 1):
            label, next_label = labels[index : index + 2]
            if label.startswith("_") and next_label.lower() in ("_tcp", "_udp"):
                return cls(
                    ".".join(labels[0:index]) or None,
                    label + "." + next_label,
                    ".".join(labels[index + 2 :]),
                )
        raise ValueError(
            f"'{name}' is not a service domain, nor a service instance name"
        )

    @property
    def ptr_name(self):
        """Return just the service name, like the name for a PTR record."""
        return ".".join((self.service, self.domain))


def qname_encode(name: typing.Union[str, typing.Sequence[str]]) -> bytes:
    """Encode QNAME without using name compression.

    Labels (each component of a domain name) are encoded using UTF-8, as that is what
    the Apple TV has been observed to use for all domain names.

    This function can take either a single string, with each label separated by dots, or
    a sequence of strings, and each element of the sequence is treated as a single
    label. A null (empty) label is added for the root domain if it is not already
    present for both types of arguments.
    """
    encoded = bytearray()
    labels: typing.List[str]
    if isinstance(name, collections.abc.Sequence) and not isinstance(name, str):
        # Copy the sequence so we can make changes to it
        labels = list(name) or []
    else:
        # Try to parse it as a service instance name, so we can handle the instance
        # label having dots in it.
        try:
            srv_name = ServiceInstanceName.split_name(name)
        except ValueError:
            labels = typing.cast(str, name).split(".")
        else:
            labels = []
            if srv_name.instance:
                labels.append(srv_name.instance)
            # the ptr_name just has the instance name dropped off
            labels.extend(srv_name.ptr_name.split("."))
    # Ensure there's always an empty label for the root domain
    if not labels or labels[-1] != "":
        labels.append("")
    # DNS-SD uses UTF-8 for names, not IDNA. Apple extends this to basically all places
    # where names are used (except for A/AAAA records, which are transliterated!).
    encoding = "utf-8"
    # Normalize all labels using NFC, as specified in RFC 6763, section 4.1.3
    normalized_labels = (unicodedata.normalize("NFC", label) for label in labels)
    for label in normalized_labels:
        encoded_label = label.encode(encoding)
        encoded_length = len(encoded_label)
        # When truncating the label, we can't just stop at 63 bytes as that might be
        # splitting a multi-byte Unicode codepoint.
        truncated = False
        while encoded_length > 63:
            truncated = True
            truncated_label = encoded_label.decode(encoding)[:-1]
            encoded_label = truncated_label.encode(encoding)
            encoded_length = len(encoded_label)
        if truncated:
            _LOGGER.warning(
                (
                    "A label (%s) is being truncated (to %s) in the DNS name '%s' "
                    "as it is over 63 bytes long."
                ),
                label,
                encoded_label.decode(encoding),
                name,
            )
        encoded.append(encoded_length)
        if encoded_length == 0:
            # If we've reached an empty label, assume this is the last component.
            # Empty labels (two periods right after each other) aren't legal anyways.
            break
        encoded.extend(encoded_label)
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
    length followed by the encoded label. The final component has a zero length
    with a null label for the DNS root. The tricky part is that labels are limited to 63
    bytes, and the upper two bits of the length are used as a flag for "name
    compression". For full details, see RFC 1035, sections 3.1 and 4.1.4.

    If labels start with the "ASCII Compatible Encoding" prefix ("xn--"), they are
    decoded with IDNA. Otherwise each label is decoded as UTF-8, as that is what is used
    for DNS-SD and Apple doesn't seem to use IDNA anywhere in their mDNS/DNS-SD stack.

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
            if label[:4] == b"xn--":
                decoded_label = label.decode("idna")
            else:
                decoded_label = label.decode("utf-8")
            labels.append(decoded_label)
    if compression_offset is not None:
        buffer.seek(compression_offset)
    return ".".join(labels)


def format_txt_dict(
    data: typing.Mapping[typing.Any, typing.Any],
) -> bytes:
    """Format a `dict` into a DNS-SD TXT record."""
    return ServiceInfo(
        "_x.local.", "_x.local.", addresses=[], port=12345, properties=data
    ).text


def parse_txt_dict(buffer: typing.BinaryIO, length: int) -> CaseInsensitiveDict[bytes]:
    """Parse DNS-SD TXT records into a `dict`."""
    output: CaseInsensitiveDict[bytes] = CaseInsensitiveDict()
    stop_position = buffer.tell() + length
    while buffer.tell() < stop_position:
        chunk = parse_string(buffer)
        if b"=" not in chunk:
            decoded_chunk = chunk.decode("ascii")
            # missing "=" means it's just present with no value.
            output[decoded_chunk] = b""
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
        if self is self.PTR:
            return parse_domain_name(buffer)
        if self is self.TXT:
            return parse_txt_dict(buffer, length)
        if self is self.SRV:
            return parse_srv_dict(buffer)
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
        data.extend(
            struct.pack(">2H", *self[1:])  # pylint: disable=unsubscriptable-object
        )
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

    def __init__(self, msg_id=0, flags=0x0120) -> None:
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

        buf = bytearray()

        buf.extend(header.pack())

        for question in self.questions:
            buf.extend(question.pack())

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
            f"MsgId=0x{self.msg_id:04X}\nFlags=0x{self.flags:04X}\n"
            f"Questions={self.questions}\nAnswers={self.answers}\n"
            f"Authorities={self.authorities}\n"
            f"Resources={self.resources}"
        )
