"""Minimalistic unicast DNS-SD implementation."""
import asyncio
import struct
import logging
from collections import namedtuple

from pyatv.support import log_binary

_LOGGER = logging.getLogger(__name__)

DnsHeader = namedtuple('DnsHeader', 'id flags qdcount ancount nscount arcount')
DnsQuestion = namedtuple('DnsQuestion', 'qname qtype qclass')
DnsAnswer = namedtuple('DnsAnswer', 'qname qtype qclass ttl rd_length rd')
DnsResource = namedtuple('DnsResource', 'qname qtype qclass ttl rd_length rd')

QTYPE_PTR = 0x000C
QTYPE_TXT = 0x0010
QTYPE_SRV = 0x0021
QTYPE_ANY = 0x00FF


def qname_encode(name):
    """Encode QNAME without using labels."""
    def _enc_word(word):
        return bytes([len(word) & 0xFF]) + word.encode('ascii')
    return b''.join([_enc_word(x) for x in name.split('.')]) + b'\x00'


def qname_decode(ptr, message, raw=False):
    """Read a QNAME from pointer and respect labels."""
    def _rec(name):
        ret = []
        while name and name[0] > 0:
            length = int(name[0])
            if (length & 0xC0) == 0xC0:
                offset = (length & 0x03) << 8 | int(name[1])
                comps, _ = _rec(message[offset:])
                ret += comps
                name = name[1:]
                break

            ret.append(name[1:1+length])
            name = name[length+1:]

        return ret, name

    name_components, rest = _rec(ptr)
    if raw:
        return name_components, rest[1:]
    return '.'.join([x.decode() for x in name_components]), rest[1:]


def parse_txt_dict(data, msg):
    """Parse DNS TXT record containing a dict."""
    output = {}
    txt, _ = qname_decode(data, msg, raw=True)
    for prop in txt:
        key, value = prop.split(b'=', 1)
        output[key] = value
    return output


def parse_srv_dict(data, msg):
    """Parse DNS SRV record."""
    priority, weight, port = struct.unpack('>HHH', data[0:6])
    return {
        'priority': priority,
        'weight': weight,
        'port': port,
        'target': qname_decode(data[6:], msg)[0],
    }


def subunpack(ptr, fmt):
    """Unpack raw data from pointer and move pointer forward."""
    unpack_size = struct.calcsize(fmt)
    data = struct.unpack(fmt, ptr[0:unpack_size])
    return ptr[unpack_size:], data


def dns_unpack(ptr, msg, fmt):
    """Unoack a generic DNS record."""
    qname, ptr = qname_decode(ptr, msg)
    ptr, data = subunpack(ptr, fmt)
    return ptr, (qname, ) + data


def unpack_rr(ptr, msg):
    """Unpack DNS resource record."""
    ptr, data = dns_unpack(ptr, msg, '>2HIH')
    _, qtype, _, _, rd_length = data
    rd_data = ptr[0:rd_length]
    ptr = ptr[rd_length:]

    if qtype == QTYPE_PTR:
        rd_data, _ = qname_decode(rd_data, msg)
    elif qtype == QTYPE_TXT:
        rd_data = parse_txt_dict(rd_data, msg)
    elif qtype == QTYPE_SRV:
        rd_data = parse_srv_dict(rd_data, msg)

    return ptr, data + (rd_data, )


def create_request(services):
    """Creste a new DnsMessage requesting specified services."""
    msg = DnsMessage(0x35Ff)
    msg.questions += [
        DnsQuestion(s, QTYPE_ANY, 0x8001) for s in services
    ]
    return msg.pack()


class DnsMessage:
    """Represent a DNS message."""

    def __init__(self, msg_id=0, flags=0x0120):
        """Initialize a new DnsMessage."""
        self.msg_id = msg_id
        self.flags = flags
        self.questions = []
        self.answers = []
        self.resources = []

    def unpack(self, msg):
        """Unpack bytes into a DnsMessage."""
        ptr, data = subunpack(msg, '>6H')
        header = DnsHeader._make(data)
        self.msg_id = header.id
        self.flags = header.flags

        if header.nscount > 0:
            raise NotImplementedError("nscount > 0")

        # Unpack questions
        for _ in range(header.qdcount):
            ptr, data = dns_unpack(ptr, msg, '>2H')
            self.questions.append(DnsQuestion(*data))

        # Unpack answers
        for _ in range(header.ancount):
            ptr, data = unpack_rr(ptr, msg)
            self.answers.append(DnsAnswer(*data))

        # Unpack additional resources
        for _ in range(header.arcount):
            ptr, data = unpack_rr(ptr, msg)
            self.resources.append(DnsResource(*data))

        return self

    def pack(self):
        """Pack message into bytes."""
        header = DnsHeader(
            self.msg_id,
            self.flags,
            len(self.questions),
            len(self.answers),
            0,
            len(self.resources))

        buf = struct.pack('>6H', *header)

        for question in self.questions:
            buf += qname_encode(question.qname)
            buf += struct.pack('>H', question.qtype)
            buf += struct.pack('>H', question.qclass)

        for answer in self.answers:
            data = qname_encode(answer.rd)
            buf += qname_encode(answer.qname)
            buf += struct.pack('>H', answer.qtype)
            buf += struct.pack('>H', answer.qclass)
            buf += struct.pack('>I', answer.ttl)
            buf += struct.pack('>H', len(data))
            buf += data

        for resource in self.resources:
            buf += qname_encode(resource.qname)
            buf += struct.pack('>H', resource.qtype)
            buf += struct.pack('>H', resource.qclass)
            buf += struct.pack('>I', resource.ttl)
            buf += struct.pack('>H', len(resource.rd))
            buf += resource.rd

        return buf

    def __str__(self):
        """Return string representation of DnsMessage."""
        return 'MsgId=0x{0:04X}\nFlags=0x{1:04X}\nQuestions={2}\n' \
            'Answers={3}\nResources={4}'.format(
                self.msg_id, self.flags, self.questions,
                self.answers, self.resources)


class UnicastDnsSdClientProtocol(asyncio.Protocol):
    """Protocol to make unicast MDNS requests."""

    def __init__(self, loop, services, host):
        """Initialize a new UnicastDnsSdClientProtocol."""
        self.message = create_request(services)
        self.host = host
        self.loop = loop
        self.transport = None
        self.semaphore = asyncio.Semaphore(value=0, loop=loop)
        self.result = None

    async def get_response(self, timeout):
        """Get respoonse with a maximum timeout."""
        await asyncio.wait_for(
            self.semaphore.acquire(), timeout=timeout, loop=self.loop)
        return self.result

    def connection_made(self, transport):
        """Establish connection to host."""
        log_binary(_LOGGER,
                   'Sending DNS request to ' + str(self.host),
                   Data=self.message)

        self.transport = transport
        self.transport.sendto(self.message)

    def datagram_received(self, data, _):
        """DNS response packet received."""
        log_binary(_LOGGER,
                   'Received DNS response from ' + str(self.host),
                   Data=data)

        self.result = DnsMessage().unpack(data)
        self.transport.close()

    def error_received(self, exc):
        """Error received during communication."""
        _LOGGER.debug('Error during DNS lookup for %s: %s', self.host, exc)
        self.semaphore.release()

    def connection_lost(self, exc):
        """Lose connection to host."""
        self.semaphore.release()


async def request(loop, address, services, port=5353, timeout=4):
    """Send request for services to a host."""
    transport, protocol = await loop.create_datagram_endpoint(
        lambda: UnicastDnsSdClientProtocol(loop, services, address),
        remote_addr=(str(address), port))

    try:
        return await protocol.get_response(timeout)
    finally:
        transport.close()
