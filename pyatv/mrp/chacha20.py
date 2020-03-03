"""Transparent encryption layer using Chacha20_Pooly1305."""
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305

from pyatv import exceptions


class Chacha20Cipher:
    """CHACHA20 encryption/decryption layer."""

    def __init__(self, out_key, in_key):
        """Initialize a new Chacha20Cipher."""
        self._enc_out = ChaCha20Poly1305(out_key)
        self._enc_in = ChaCha20Poly1305(in_key)
        self._out_counter = 0
        self._in_counter = 0

    def encrypt(self, data, nounce=None):
        """Encrypt data with counter or specified nounce."""
        if nounce is None:
            nounce = self._out_counter.to_bytes(length=8, byteorder="little")
            self._out_counter += 1

        return self._enc_out.encrypt(b"\x00\x00\x00\x00" + nounce, data, None)

    def decrypt(self, data, nounce=None):
        """Decrypt data with counter or specified nounce."""
        if nounce is None:
            nounce = self._in_counter.to_bytes(length=8, byteorder="little")
            self._in_counter += 1

        decrypted = self._enc_in.decrypt(b"\x00\x00\x00\x00" + nounce, data, None)

        if not decrypted:
            raise exceptions.AuthenticationError("data decrypt failed")

        return bytes(decrypted)
