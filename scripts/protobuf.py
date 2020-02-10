#!/usr/bin/env python3
"""Simple tool to work with protobuf in pyatv."""

import os
import sys
import glob
import binascii
import argparse
import subprocess
from collections import namedtuple

import cryptography
from google.protobuf.text_format import MessageToString
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305

from pyatv.mrp import variant
from pyatv.mrp.protobuf import ProtocolMessage_pb2 as PB


# New messages re-using inner message of another type
REUSED_MESSAGES = {"DEVICE_INFO_MESSAGE": "DEVICE_INFO_UPDATE_MESSAGE"}

BASE_PATH = os.path.join("pyatv", "mrp", "protobuf")
OUTPUT_TEMPLATE = """\"\"\"Simplified extension handling for protobuf messages.

THIS CODE IS AUTO-GENERATED - DO NOT EDIT!!!
\"\"\"

from .ProtocolMessage_pb2 import ProtocolMessage


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


ProtocolMessage.inner = _inner_message  # type: ignore
"""

MessageInfo = namedtuple(
    "MessageInfo", ["module", "title", "accessor", "const"])


def extract_message_info():
    """Get information about all messages of interest."""
    filename = os.path.join(BASE_PATH, "ProtocolMessage.proto")

    with open(filename, "r") as file:
        types_found = False

        for line in file:
            stripped = line.lstrip().rstrip()

            # Look for the Type enum
            if stripped == "enum Type {":
                types_found = True
                continue
            elif types_found and stripped == "}":
                break
            elif not types_found:
                continue

            constant = stripped.split(" ")[0]
            title = constant.title().replace(
                "_", "").replace("Hid", "HID")  # Hack...
            accessor = title[0].lower() + title[1:]

            if not os.path.exists(os.path.join(BASE_PATH, title + ".proto")):
                continue

            yield MessageInfo(title + "_pb2", title, accessor, constant)


def extract_unreferenced_messages():
    """Get messages not referenced anywhere."""
    for filename in os.listdir(BASE_PATH):
        tmp = os.path.splitext(filename)
        if tmp[1] != ".proto" or tmp[0] == "ProtocolMessage":
            continue

        with open(os.path.join(BASE_PATH, filename)) as file:
            for line in file:
                if line.startswith("message"):
                    yield tmp[0] + "_pb2", line.split(" ")[1]


def generate_module_code():
    """Generate protobuf message wrappercode."""
    message_names = set()
    packages = []
    messages = []
    extensions = []
    constants = []

    # Extract everything needed to generate output file
    for info in extract_message_info():
        message_names.add(info.title)
        packages.append("from . import " + info.module)
        messages.append("from .{0} import {1}".format(info.module, info.title))
        extensions.append(
            "ProtocolMessage.{0}: {1}.{2},".format(
                info.const, info.module, info.accessor
            )
        )
        constants.append("{0} = ProtocolMessage.{0}".format(info.const))

        reused = REUSED_MESSAGES.get(info.const)
        if reused:
            extensions.append(
                "ProtocolMessage.{0}: {1}.{2},".format(
                    reused, info.module, info.accessor
                )
            )

    # Look for remaining messages
    for module_name, message_name in extract_unreferenced_messages():
        if message_name not in message_names:
            message_names.add(message_name)
            messages.append(
                "from .{0} import {1}".format(module_name, message_name))

    return OUTPUT_TEMPLATE.format(
            packages="\n".join(sorted(packages)),
            messages="\n".join(sorted(messages)),
            extensions="\n    ".join(sorted(extensions)),
            constants="\n".join(sorted(constants)),
        )


def update_auto_generated_code():
    """Generate and update auto-generated wrapper code."""
    if not os.path.exists(".git"):
        print("Run this script from repo root", file=sys.stderr)
        return 1

    proto_files = glob.glob(os.path.join(BASE_PATH, "*.proto"))
    subprocess.run(["protoc",
                    "--proto_path=.",
                    "--python_out=.",
                    "--mypy_out=."] + proto_files)

    module_code = generate_module_code()
    with open(os.path.join(BASE_PATH, "__init__.py"), "w") as fh:
        fh.write(module_code)

    return 0


def _print_single_message(data, unknown_fields):
    parsed = PB.ProtocolMessage()
    parsed.ParseFromString(data)
    output = MessageToString(
        parsed, print_unknown_fields=unknown_fields)
    print(output)


def decode_and_print_message(args):
    """Decode and print protobuf messages."""
    buf = binascii.unhexlify(args.message)
    if not args.stream:
        buf = variant.write_variant(len(buf)) + buf

    while buf:
        length, raw = variant.read_variant(buf)
        data = raw[:length]
        buf = raw[length:]
        _print_single_message(data, args.unknown_fields)

    return 0


def _decrypt_chacha20poly1305(data, nounce, key):
    """Decrypt data with specified key and nounce."""
    data = binascii.unhexlify(data)
    input_key = binascii.unhexlify(key)
    input_nonce = b'\x00\x00\x00\x00' + nounce.to_bytes(
        length=8, byteorder='little')
    chacha = ChaCha20Poly1305(input_key)
    try:
        print('Trying key {0} with nounce {1}'.format(input_key, input_nonce))
        decrypted_data = chacha.decrypt(input_nonce, data, None)
        print('Data decrypted!\n - Nounce : {0}'
              '\n - Key    : {1}\n - Data   : {2}\n'.format(
                binascii.hexlify(input_nonce).decode(),
                binascii.hexlify(input_key).decode(),
                binascii.hexlify(decrypted_data).decode()))
        _print_single_message(decrypted_data, True)
        return True
    except cryptography.exceptions.InvalidTag:
        pass

    return False


def decrypt_and_print_message(args):
    """Try to decrypt and print a message."""
    for key in args.keys:
        for nounce in range(args.nounce_lower, args.nounce_upper):
            if _decrypt_chacha20poly1305(args.message, nounce, key):
                return 0
    return 1


def main():
    """Script starts here."""
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(help="sub commands", dest="command")

    subparsers.add_parser("generate", help="generate protobuf wrapper")

    decode = subparsers.add_parser("decode", help="decode protobuf message(s)")
    decode.add_argument("message", help="message in hex to decode")
    decode.add_argument("-u", "--unknown-fields", action="store_true",
                        help="include unknown fields")
    decode.add_argument("-s", "--stream", action="store_true",
                        help="decode protocol stream of messages")

    decrypt = subparsers.add_parser("decrypt", help="decrypt protobuf message")
    decrypt.add_argument("message", help="message in hex to decrypt")
    decrypt.add_argument("keys", nargs="+", help="keys to decrypt with")
    decrypt.add_argument("-l", "--nounce-lower", type=int, default=0,
                         help="start value for nounce")
    decrypt.add_argument("-u", "--nounce-upper", type=int, default=128,
                         help="upper value for nounce")

    args = parser.parse_args()
    if not args.command:
        parser.error("No command specified")
        return 1

    if args.command == "generate":
        return update_auto_generated_code()
    elif args.command == "decode":
        return decode_and_print_message(args)
    elif args.command == "decrypt":
        return decrypt_and_print_message(args)

    return 1


if __name__ == "__main__":
    sys.exit(main())
