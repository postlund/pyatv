#!/usr/bin/env python3

import sys
import binascii

from pyatv.mrp.protobuf import ProtocolMessage_pb2 as PB


if __name__ == '__main__':
    data = binascii.unhexlify(sys.argv[1])
    parsed = PB.ProtocolMessage()
    parsed.ParseFromString(data)
    print(parsed)
