#!/usr/bin/env python3
#
# This is a quick-hack that extends ProtocolMessage with a method called inner
# that will return the correct submessage based on the type.
#
# Update with this command:
# ./scripts/autogen_protobuf_extensions.py > pyatv/mrp/protobuf/__init__.py
#
"""Simple hack to auto-generate protobuf handling code."""

import sys
import os
from collections import namedtuple


BASE_PACKAGE = 'pyatv.mrp.protobuf'
OUTPUT_TEMPLATE = """\"\"\"Simplified extension handling for protobuf messages.

THIS CODE IS AUTO-GENERATED - DO NOT EDIT!!!
\"\"\"

from pyatv.mrp.protobuf.ProtocolMessage_pb2 import ProtocolMessage


{packages}


{messages}


_EXTENSION_LOOKUP = {{
    {extensions}
}}


{constants}


def _inner_message(self):
    extension = _EXTENSION_LOOKUP.get(self.type, None)
    if extension:
        return self.Extensions[extension]

    raise Exception('unknown type: ' + str(self.type))


ProtocolMessage.inner = _inner_message
"""

MessageInfo = namedtuple('MessageInfo',
                         ['module', 'title', 'accessor', 'const'])


def extract_message_info():
    """Get information about all messages of interest."""
    base_path = BASE_PACKAGE.replace('.', '/')
    filename = os.path.join(base_path, 'ProtocolMessage.proto')

    with open(filename, 'r') as file:
        types_found = False

        for line in file:
            stripped = line.lstrip().rstrip()

            # Look for the Type enum
            if stripped == 'enum Type {':
                types_found = True
                continue
            elif types_found and stripped == '}':
                break
            elif not types_found:
                continue

            constant = stripped.split(' ')[0]
            title = constant.title().replace(
                '_', '').replace('Hid', 'HID')  # Hack...
            accessor = title[0].lower() + title[1:]

            if not os.path.exists(os.path.join(base_path, title + '.proto')):
                continue

            yield MessageInfo(
                title + '_pb2', title, accessor, constant)


def main():
    """Script starts somewhere around here."""
    packages = []
    messages = []
    extensions = []
    constants = []

    # Extract everything needed to generate output file
    for info in extract_message_info():
        packages.append(
            'from {0} import {1}'.format(
                BASE_PACKAGE, info.module))
        messages.append(
            'from {0}.{1} import {2}'.format(
                BASE_PACKAGE, info.module, info.title))
        extensions.append(
            'ProtocolMessage.{0}: {1}.{2},'.format(
                info.const, info.module, info.accessor))
        constants.append(
            '{0} = ProtocolMessage.{0}'.format(
                info.const))

    # Print file output with values inserted
    print(OUTPUT_TEMPLATE.format(
        packages='\n'.join(packages),
        messages='\n'.join(messages),
        extensions='\n    '.join(extensions),
        constants='\n'.join(constants)))

    return 0


if __name__ == '__main__':
    sys.exit(main())
