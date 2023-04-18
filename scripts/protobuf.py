#!/usr/bin/env python3
"""Simple tool to work with protobuf in pyatv."""

import argparse
import binascii
from collections import namedtuple
import difflib
import glob
from io import BytesIO
import os
import re
import stat
import subprocess
import sys
import zipfile

import cryptography
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from google.protobuf.text_format import MessageToString
import requests

# New messages re-using inner message of another type
REUSED_MESSAGES = {"DEVICE_INFO_MESSAGE": "DEVICE_INFO_UPDATE_MESSAGE"}

BASE_PATH = os.path.join("pyatv", "protocols", "mrp", "protobuf")
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

MessageInfo = namedtuple("MessageInfo", ["module", "title", "accessor", "const"])


def _protobuf_url(version):
    base_url = (
        "https://github.com/protocolbuffers/protobuf/"
        + "releases/download/v{version}/protoc-{version}-{platform}.zip"
    )
    platforms = {
        "linux": "linux-x86_64",
        "darwin": "osx-x86_64",
        "win32": "win64",
    }

    platform = platforms.get(sys.platform)
    if not platform:
        print("Unsupported platform: " + sys.platform, file=sys.stderr)
        sys.exit(1)

    return base_url.format(version=version, platform=platform)


def _get_protobuf_version():
    with open("base_versions.txt", encoding="utf-8") as file:
        for line in file:
            match = re.match(r"protobuf==(\d+\.\d+\.\d+)[^0-9,]*", line)
            if match:
                return match.group(1)
    raise RuntimeError("failed to determine protobuf version")


def _download_protoc(force=False):
    if os.path.exists(protoc_path()) and not force:
        print("Not downloading protoc (already exists)")
        return

    version = _get_protobuf_version()
    url = _protobuf_url(version)

    print("Downloading", url)

    resp = requests.get(url, timeout=10)
    with zipfile.ZipFile(BytesIO(resp.content)) as zip_file:
        for zip_info in zip_file.infolist():
            if zip_info.filename.startswith("bin/protoc"):
                print("Extracting", zip_info.filename)
                basename, extension = os.path.splitext(zip_info.filename)
                zip_info.filename = f"{basename}-{version}{extension}"
                zip_file.extract(zip_info)
                break

    if not os.path.exists(protoc_path()):
        print(protoc_path(), "was not downloaded correctly", file=sys.stderr)
        sys.exit(1)

    file_stat = os.stat(protoc_path())
    os.chmod(protoc_path(), file_stat.st_mode | stat.S_IEXEC)


def _verify_protoc_version():
    expected_version = _get_protobuf_version()
    try:
        ret = subprocess.run(
            [protoc_path(), "--version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        installed_version = ret.stdout.decode("utf-8").split(" ")[1].rstrip()
        if installed_version != expected_version:
            print(
                "Expected protobuf",
                expected_version,
                "but found",
                installed_version,
                file=sys.stderr,
            )
            sys.exit(1)
    except FileNotFoundError:
        print(
            "Protbuf compiler (protoc) not found. Re-run with --download",
            file=sys.stderr,
        )
        sys.exit(1)
    else:
        print(f"Using protobuf version {expected_version}")


def protoc_path():
    """Return path to protoc binary."""
    binary = f"protoc-{_get_protobuf_version()}" + (
        ".exe" if sys.platform == "win32" else ""
    )
    return os.path.join("bin", binary)


def extract_message_info():
    """Get information about all messages of interest."""
    filename = os.path.join(BASE_PATH, "ProtocolMessage.proto")

    with open(filename, encoding="utf-8", mode="r") as file:
        types_found = False

        for line in file:
            stripped = line.lstrip().rstrip()

            # Look for the Type enum
            if stripped == "enum Type {":
                types_found = True
                continue
            if types_found and stripped == "}":
                break
            if not types_found:
                continue

            constant = stripped.split(" ")[0]
            title = constant.title().replace("_", "").replace("Hid", "HID")  # Hack...
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

        with open(os.path.join(BASE_PATH, filename), encoding="utf-8") as file:
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
        messages.append(f"from .{info.module} import {info.title}")
        extensions.append(
            f"ProtocolMessage.{info.const}: {info.module}.{info.accessor},"
        )
        constants.append(f"{info.const} = ProtocolMessage.{info.const}")

        reused = REUSED_MESSAGES.get(info.const)
        if reused:
            extensions.append(
                f"ProtocolMessage.{reused}: {info.module}.{info.accessor},"
            )
            constants.append(f"{reused} = ProtocolMessage.{reused}")

    # Look for remaining messages
    for module_name, message_name in extract_unreferenced_messages():
        if message_name not in message_names:
            message_names.add(message_name)
            messages.append(f"from .{module_name} import {message_name}")

    return OUTPUT_TEMPLATE.format(
        packages="\n".join(sorted(packages)),
        messages="\n".join(sorted(messages)),
        extensions="\n    ".join(sorted(extensions)),
        constants="\n".join(sorted(constants)),
    )


def update_auto_generated_code():
    """Generate and update auto-generated wrapper code."""
    proto_files = glob.glob(os.path.join(BASE_PATH, "*.proto"))
    subprocess.run(
        [protoc_path(), "--proto_path=.", "--python_out=.", "--mypy_out=."]
        + proto_files,
        check=False,
    )

    module_code = generate_module_code()
    with open(os.path.join(BASE_PATH, "__init__.py"), encoding="utf-8", mode="w") as f:
        f.write(module_code)

    return 0


def verify_generated_code():
    """Verify that generated code is up-to-date."""
    generated_code = generate_module_code().splitlines(True)

    with open(os.path.join(BASE_PATH, "__init__.py"), encoding="utf-8", mode="r") as f:
        actual = f.readlines()

        diff = list(
            difflib.unified_diff(
                actual, generated_code, fromfile="current", tofile="updated"
            )
        )
        if diff:
            print("Generated code is NOT up-to-date!", file=sys.stderr)
            print(15 * "*", file=sys.stderr)
            print("".join(diff), file=sys.stderr)
            print(15 * "*", file=sys.stderr)
            print("Re-run with generate to update code.", file=sys.stderr)
            return 1

    print("Generated code is up-to-date!")

    return 0


def _print_single_message(data, unknown_fields):
    # Import here to allow other parts of script, e.g. message generation to run
    # without having pyatv installed
    # pylint: disable=import-outside-toplevel
    from pyatv.protocols.mrp.protobuf import ProtocolMessage

    # pylint: enable=import-outside-toplevel

    parsed = ProtocolMessage()
    parsed.ParseFromString(data)

    # The print_unknown_fields is only available in newer versions of protobuf
    # (from 3.8 or so). This script is generally only run with newer versions than
    # that, so we can disable pylint here.
    output = MessageToString(  # pylint: disable=unexpected-keyword-arg
        parsed, print_unknown_fields=unknown_fields
    )
    print(output)


def decode_and_print_message(args):
    """Decode and print protobuf messages."""
    # Import here to allow other parts of script, e.g. message generation to run
    # without having pyatv installed
    from pyatv.support import variant  # pylint: disable=import-outside-toplevel

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
    input_nonce = b"\x00\x00\x00\x00" + nounce.to_bytes(length=8, byteorder="little")
    chacha = ChaCha20Poly1305(input_key)
    try:
        print(f"Trying key {input_key} with nounce {input_nonce}")
        decrypted_data = chacha.decrypt(input_nonce, data, None)
        print(
            "Data decrypted!"
            f"\n - Nonce : {binascii.hexlify(input_nonce).decode()}"
            f"\n - Key   : {binascii.hexlify(input_key).decode()}"
            f"\n - Data  : {binascii.hexlify(decrypted_data).decode()}\n"
        )
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


def main():  # pylint: disable=too-many-return-statements
    """Script starts here."""
    if not os.path.exists(".git"):
        print("Run this script from repo root", file=sys.stderr)
        return 1

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-d",
        "--download",
        action="store_true",
        help="download protobuf compiler",
    )
    parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="force download if already downloaded",
    )

    subparsers = parser.add_subparsers(help="sub commands", dest="command")
    subparsers.add_parser("generate", help="generate protobuf wrapper")
    subparsers.add_parser("verify", help="verify wrapper is up-to-date")

    decode = subparsers.add_parser("decode", help="decode protobuf message(s)")
    decode.add_argument("message", help="message in hex to decode")
    decode.add_argument(
        "-u",
        "--unknown-fields",
        action="store_true",
        help="include unknown fields",
    )
    decode.add_argument(
        "-s",
        "--stream",
        action="store_true",
        help="decode protocol stream of messages",
    )

    decrypt = subparsers.add_parser("decrypt", help="decrypt protobuf message")
    decrypt.add_argument("message", help="message in hex to decrypt")
    decrypt.add_argument("keys", nargs="+", help="keys to decrypt with")
    decrypt.add_argument(
        "-l",
        "--nounce-lower",
        type=int,
        default=0,
        help="start value for nounce",
    )
    decrypt.add_argument(
        "-u",
        "--nounce-upper",
        type=int,
        default=128,
        help="upper value for nounce",
    )

    args = parser.parse_args()
    if not args.command:
        parser.error("No command specified")
        return 1

    if args.command == "generate":
        if args.download:
            _download_protoc(args.force)
        _verify_protoc_version()
        return update_auto_generated_code()
    if args.command == "verify":
        if args.download:
            _download_protoc(args.force)
        _verify_protoc_version()
        return verify_generated_code()
    if args.command == "decode":
        return decode_and_print_message(args)
    if args.command == "decrypt":
        return decrypt_and_print_message(args)

    return 1


if __name__ == "__main__":
    sys.exit(main())
