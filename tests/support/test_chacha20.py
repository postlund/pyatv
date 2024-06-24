"""Unit tests for pyatv.support.chacha20."""

import logging

from pyatv.support import chacha20

fake_key = b"k" * 32


def test_12_bytes_nonce():
    cipher = chacha20.Chacha20Cipher(fake_key, fake_key, 12)
    assert len(cipher.out_nonce) == chacha20.NONCE_LENGTH
    assert len(cipher.in_nonce) == chacha20.NONCE_LENGTH
    result = cipher.encrypt(b"test")
    assert cipher.decrypt(result) == b"test"


def test_8_bytes_nonce():
    cipher = chacha20.Chacha20Cipher8byteNonce(fake_key, fake_key)
    assert len(cipher.out_nonce) == chacha20.NONCE_LENGTH
    assert len(cipher.in_nonce) == chacha20.NONCE_LENGTH
    result = cipher.encrypt(b"test")
    assert cipher.decrypt(result) == b"test"
