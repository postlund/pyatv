"""Cryptograhpy routines used by HAP."""

from typing import Optional

from pyatv.support.chacha20 import Chacha20Cipher


class HAPSession:
    """Manages cryptography for a HAP session according to IP in specification.

    The HAP specification mandates that data is encrypted/decrypted in blocks
    of 1024 bytes. This class takes care of that. It is designed to be
    transparent until encryption is enabled, i.e. data is just passed through
    in case it has not yet been enabled.
    """

    FRAME_LENGTH = 1024  # As specified by HAP, section 5.2.2 (Release R1)
    AUTH_TAG_LENGTH = 16

    def __init__(
        self,
    ) -> None:
        """Initialize a new HAPSession instance."""
        self._encrypted_data = b""
        self.chacha20: Optional[Chacha20Cipher] = None

    def enable(self, output_key: bytes, input_key: bytes) -> None:
        """Enable encryption with specified keys."""
        self.chacha20 = Chacha20Cipher(output_key, input_key)

    def decrypt(self, data: bytes) -> bytes:
        """Decrypt incoming data."""
        if self.chacha20 is None:
            return data

        self._encrypted_data += data

        output = b""
        while self._encrypted_data:
            length = self._encrypted_data[0:2]
            block_length = (
                int.from_bytes(length, byteorder="little") + self.AUTH_TAG_LENGTH
            )
            if len(self._encrypted_data) < block_length + 2:
                return output

            block = self._encrypted_data[2 : 2 + block_length]
            output += self.chacha20.decrypt(block, aad=length)

            self._encrypted_data = self._encrypted_data[2 + block_length :]
        return output

    def encrypt(self, data: bytes) -> bytes:
        """Encrypt outgoing data."""
        if self.chacha20 is None:
            return data

        output = b""
        while data:
            frame = data[0 : self.FRAME_LENGTH]
            data = data[self.FRAME_LENGTH :]

            length = int.to_bytes(len(frame), 2, byteorder="little")
            frame = self.chacha20.encrypt(frame, aad=length)
            output += length + frame
        return output
