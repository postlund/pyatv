#!/usr/bin/env python3
#
# Simple helper script that tries to decrypt CHACHA20 encrypted data with
# specified keys and some nounces. Just update constans below and run
# the script:
#
# $ ./bruteforce.py
# ...
# Data decrypted!
#  - Nounce : 000000000000000000000000
#  - Key    : 7f0a54c5b15ccafc4927582c11d3394a55c95e489e72d12222a91b06f34c6094
#  - Data   : 080b200082012d0a2b6b4d5254656c65766973696f6e52656d6f74654e6f7750
#             6c6179696e67417274776f726b4368616e676564
#
"""Manually decrypt some ChaCha20Poly1305 encrypted data."""

import sys
import binascii
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305


# Example data
DATA = "E8E786E4E673A38808063FEFDAF79D66B99C0745DA45C704DE51D4855FAE752F3" \
    "B92ECA29E1DF5EF6B48C72BE4E87FC660BF5CE57D768365E60397E7C97D16AB233441B9"
KEYS = ["70743888c9eda99d1a24c5a94a26f85a0fec26f4cba16f919e5c23f892ecfbab",
        "7f0a54c5b15ccafc4927582c11d3394a55c95e489e72d12222a91b06f34c6094"]


def decrypt(data, nounce, key):
    """Decrypt data with specified key and nounce."""
    data = binascii.unhexlify(data.replace(' ', ''))
    input_key = binascii.unhexlify(key.replace(' ', ''))
    input_nonce = b'\x00\x00\x00\x00' + nounce.to_bytes(
        length=8, byteorder='little')
    chacha = ChaCha20Poly1305(input_key)
    try:
        print('Trying key {0} with nounce {1}'.format(input_key, input_nonce))
        decrypted_data = chacha.decrypt(input_nonce, data, None)
        print('Data decrypted!\n - Nounce : {0}'
              '\n - Key    : {1}\n - Data   : {2}'.format(
                binascii.hexlify(input_nonce).decode(),
                binascii.hexlify(input_key).decode(),
                binascii.hexlify(decrypted_data).decode()))
        sys.exit(0)
    except Exception:  # pylint: disable=broad-except
        pass


def main(key_set):
    """Script starts here."""
    for key in key_set:
        for nounce in range(128):
            decrypt(DATA, nounce, key)


if __name__ == '__main__':
    main(KEYS)
