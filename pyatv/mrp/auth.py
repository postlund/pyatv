"""Device pairing and derivation of encryption keys."""

import logging

from pyatv import exceptions
from pyatv.mrp import messages
from pyatv.support import log_binary
from pyatv.support.hap_tlv8 import TlvValue, read_tlv, stringify

_LOGGER = logging.getLogger(__name__)


def _get_pairing_data(resp):
    tlv = read_tlv(resp.inner().pairingData)
    if TlvValue.Error in tlv:
        raise exceptions.AuthenticationError(stringify(tlv))
    return tlv


class MrpPairingProcedure:
    """Perform pairing and return new credentials."""

    def __init__(self, protocol, srp):
        """Initialize a new MrpPairingHandler."""
        self.protocol = protocol
        self.srp = srp
        self._atv_salt = None
        self._atv_pub_key = None

    async def start_pairing(self):
        """Start pairing procedure."""
        self.srp.initialize()

        await self.protocol.start(skip_initial_messages=True)

        msg = messages.crypto_pairing(
            {TlvValue.Method: b"\x00", TlvValue.SeqNo: b"\x01"},
            is_pairing=True,
        )
        resp = await self.protocol.send_and_receive(msg, generate_identifier=False)

        pairing_data = _get_pairing_data(resp)
        self._atv_salt = pairing_data[TlvValue.Salt]
        self._atv_pub_key = pairing_data[TlvValue.PublicKey]

    async def finish_pairing(self, pin):
        """Finish pairing process."""
        self.srp.step1(pin)

        pub_key, proof = self.srp.step2(self._atv_pub_key, self._atv_salt)

        msg = messages.crypto_pairing(
            {
                TlvValue.SeqNo: b"\x03",
                TlvValue.PublicKey: pub_key,
                TlvValue.Proof: proof,
            }
        )
        resp = await self.protocol.send_and_receive(msg, generate_identifier=False)

        pairing_data = _get_pairing_data(resp)
        atv_proof = pairing_data[TlvValue.Proof]
        log_binary(_LOGGER, "Device", Proof=atv_proof)

        encrypted_data = self.srp.step3()
        msg = messages.crypto_pairing(
            {TlvValue.SeqNo: b"\x05", TlvValue.EncryptedData: encrypted_data}
        )
        resp = await self.protocol.send_and_receive(msg, generate_identifier=False)

        pairing_data = _get_pairing_data(resp)
        encrypted_data = pairing_data[TlvValue.EncryptedData]

        return self.srp.step4(encrypted_data)


class MrpPairingVerifier:
    """Verify credentials and derive new encryption keys."""

    def __init__(self, protocol, srp, credentials):
        """Initialize a new MrpPairingVerifier."""
        self.protocol = protocol
        self.srp = srp
        self.credentials = credentials
        self._output_key = None
        self._input_key = None

    async def verify_credentials(self):
        """Verify credentials with device."""
        _, public_key = self.srp.initialize()

        msg = messages.crypto_pairing(
            {TlvValue.SeqNo: b"\x01", TlvValue.PublicKey: public_key}
        )
        resp = await self.protocol.send_and_receive(msg, generate_identifier=False)

        resp = _get_pairing_data(resp)
        session_pub_key = resp[TlvValue.PublicKey]
        encrypted = resp[TlvValue.EncryptedData]
        log_binary(_LOGGER, "Device", Public=self.credentials.ltpk, Encrypted=encrypted)

        encrypted_data = self.srp.verify1(self.credentials, session_pub_key, encrypted)
        msg = messages.crypto_pairing(
            {TlvValue.SeqNo: b"\x03", TlvValue.EncryptedData: encrypted_data}
        )
        await self.protocol.send_and_receive(msg, generate_identifier=False)

        # TODO: check status code

        self._output_key, self._input_key = self.srp.verify2()

    def encryption_keys(self):
        """Return derived encryption keys."""
        return self._output_key, self._input_key
