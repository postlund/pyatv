#!/usr/bin/env python3
"""Raw decode sequence of messages with protoc.

Pass hex string (including variant length). Multiple messages
are supported.
"""

import os
import sys
import binascii

from pyatv.mrp import variant


if __name__ == '__main__':
    buf = binascii.unhexlify(sys.argv[1])
    while buf:
        length, raw = variant.read_variant(buf)
        data = raw[:length]
        buf = raw[length:]

        hexdata = binascii.hexlify(data).decode('ascii')
        print('Raw:', hexdata, '\n')
        print('Decoded')
        os.system('echo ' + hexdata + ' | xxd -r -p | protoc --decode_raw')
        print(40*'-')
