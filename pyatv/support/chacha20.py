"""Transparent encryption layer using Chacha20_Pooly1305."""
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305

NONCE_LENGTH = 12


class Chacha20Cipher:
    """CHACHA20 encryption/decryption layer."""

    def __init__(self, out_key, in_key, nonce_length=8):
        """Initialize a new Chacha20Cipher."""
        self._enc_out = ChaCha20Poly1305(out_key)
        self._enc_in = ChaCha20Poly1305(in_key)
        self._out_counter = 0
        self._in_counter = 0
        self._nonce_length = nonce_length

    def encrypt(self, data, nounce=None, aad=None):
        """Encrypt data with counter or specified nounce."""
        if nounce is None:
            nounce = self._out_counter.to_bytes(
                length=self._nonce_length, byteorder="little"
            )
            self._out_counter += 1

        if len(nounce) < NONCE_LENGTH:
            nounce = b"\x00" * (NONCE_LENGTH - len(nounce)) + nounce

        return self._enc_out.encrypt(nounce, data, aad)

    def decrypt(self, data, nounce=None, aad=None):
        """Decrypt data with counter or specified nounce."""
        if nounce is None:
            nounce = self._in_counter.to_bytes(
                length=self._nonce_length, byteorder="little"
            )
            self._in_counter += 1

        if len(nounce) < NONCE_LENGTH:
            nounce = b"\x00" * (NONCE_LENGTH - len(nounce)) + nounce

        decrypted = self._enc_in.decrypt(nounce, data, aad)

        return bytes(decrypted)
