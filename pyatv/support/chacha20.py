"""Transparent encryption layer using Chacha20_Poly1305."""
from functools import partial
from struct import Struct
from typing import Optional

from chacha20poly1305_reuseable import ChaCha20Poly1305Reusable as ChaCha20Poly1305

NONCE_LENGTH = 12

# The first 4 bytes are always 0, followed by 8 bytes of counter
# for a total of 12 bytes.
PACK_NONCE = partial(Struct("<LQ").pack, 0)


class Chacha20Cipher:
    """CHACHA20 encryption/decryption layer."""

    def __init__(self, out_key, in_key, nonce_length=8):
        """Initialize a new Chacha20Cipher."""
        self._enc_out = ChaCha20Poly1305(out_key)
        self._enc_in = ChaCha20Poly1305(in_key)
        self._out_counter = 0
        self._in_counter = 0
        self._nonce_length = nonce_length

    @property
    def out_nonce(self) -> bytes:
        """Return next encrypt nonce.

        This is the nonce that will be used by encrypt in the _next_ call if no custom
        nonce is specified.
        """
        return PACK_NONCE(self._out_counter)

    @property
    def in_nonce(self) -> bytes:
        """Return next decrypt nonce.

        This is the nonce that will be used by decrypt in the _next_ call if no custom
        nonce is specified.
        """
        return PACK_NONCE(self._in_counter)

    def encrypt(
        self, data: bytes, nonce: Optional[bytes] = None, aad: Optional[bytes] = None
    ) -> bytes:
        """Encrypt data with counter or specified nonce."""
        if nonce is None:
            nonce = self.out_nonce
            self._out_counter += 1
        if len(nonce) < NONCE_LENGTH:
            nonce = b"\x00" * (NONCE_LENGTH - len(nonce)) + nonce            
        return self._enc_out.encrypt(nonce, data, aad)

    def decrypt(
        self, data: bytes, nonce: Optional[bytes] = None, aad: Optional[bytes] = None
    ) -> bytes:
        """Decrypt data with counter or specified nonce."""
        if nonce is None:
            nonce = self.in_nonce
            self._in_counter += 1
        if len(nonce) < NONCE_LENGTH:
            nonce = b"\x00" * (NONCE_LENGTH - len(nonce)) + nonce            
        return self._enc_in.decrypt(nonce, data, aad)
