"""Device pairing and derivation of encryption keys."""

import logging

from pyatv import exceptions
from pyatv.support import log_binary, hap_tlv8
from pyatv.mrp import messages
from pyatv.mrp.protobuf import CryptoPairingMessage_pb2 as CryptoPairingMessage

_LOGGER = logging.getLogger(__name__)


def _get_pairing_data(resp):
    pairing_message = CryptoPairingMessage.cryptoPairingMessage
    tlv = hap_tlv8.read_tlv(resp.Extensions[pairing_message].pairingData)
    if hap_tlv8.TLV_ERROR in tlv:
        error = int.from_bytes(tlv[hap_tlv8.TLV_ERROR], byteorder="little")
        raise exceptions.AuthenticationError("got error: " + str(error))
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
            {hap_tlv8.TLV_METHOD: b"\x00", hap_tlv8.TLV_SEQ_NO: b"\x01"},
            is_pairing=True,
        )
        resp = await self.protocol.send_and_receive(msg, generate_identifier=False)

        pairing_data = _get_pairing_data(resp)

        if hap_tlv8.TLV_BACK_OFF in pairing_data:
            time = int.from_bytes(
                pairing_data[hap_tlv8.TLV_BACK_OFF], byteorder="little"
            )
            raise exceptions.BackOffError(
                "please wait {0}s before trying again".format(time)
            )

        self._atv_salt = pairing_data[hap_tlv8.TLV_SALT]
        self._atv_pub_key = pairing_data[hap_tlv8.TLV_PUBLIC_KEY]

    async def finish_pairing(self, pin):
        """Finish pairing process."""
        self.srp.step1(pin)

        pub_key, proof = self.srp.step2(self._atv_pub_key, self._atv_salt)

        msg = messages.crypto_pairing(
            {
                hap_tlv8.TLV_SEQ_NO: b"\x03",
                hap_tlv8.TLV_PUBLIC_KEY: pub_key,
                hap_tlv8.TLV_PROOF: proof,
            }
        )
        resp = await self.protocol.send_and_receive(msg, generate_identifier=False)

        pairing_data = _get_pairing_data(resp)
        atv_proof = pairing_data[hap_tlv8.TLV_PROOF]
        log_binary(_LOGGER, "Device", Proof=atv_proof)

        encrypted_data = self.srp.step3()
        msg = messages.crypto_pairing(
            {hap_tlv8.TLV_SEQ_NO: b"\x05", hap_tlv8.TLV_ENCRYPTED_DATA: encrypted_data}
        )
        resp = await self.protocol.send_and_receive(msg, generate_identifier=False)

        pairing_data = _get_pairing_data(resp)
        encrypted_data = pairing_data[hap_tlv8.TLV_ENCRYPTED_DATA]

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
            {hap_tlv8.TLV_SEQ_NO: b"\x01", hap_tlv8.TLV_PUBLIC_KEY: public_key}
        )
        resp = await self.protocol.send_and_receive(msg, generate_identifier=False)

        resp = _get_pairing_data(resp)
        session_pub_key = resp[hap_tlv8.TLV_PUBLIC_KEY]
        encrypted = resp[hap_tlv8.TLV_ENCRYPTED_DATA]
        log_binary(_LOGGER, "Device", Public=self.credentials.ltpk, Encrypted=encrypted)

        encrypted_data = self.srp.verify1(self.credentials, session_pub_key, encrypted)
        msg = messages.crypto_pairing(
            {hap_tlv8.TLV_SEQ_NO: b"\x03", hap_tlv8.TLV_ENCRYPTED_DATA: encrypted_data}
        )
        await self.protocol.send_and_receive(msg, generate_identifier=False)

        # TODO: check status code

        self._output_key, self._input_key = self.srp.verify2()

    def encryption_keys(self):
        """Return derived encryption keys."""
        return self._output_key, self._input_key
