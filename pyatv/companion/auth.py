"""Device pairing and derivation of encryption keys."""
import logging
from typing import Dict, Tuple

from pyatv import exceptions
from pyatv.companion import opack
from pyatv.companion.connection import FrameType
from pyatv.support import hap_tlv8, log_binary
from pyatv.support.hap_srp import HapCredentials, SRPAuthHandler
from pyatv.support.hap_tlv8 import TlvValue, read_tlv, stringify

_LOGGER = logging.getLogger(__name__)

SRP_SALT = ""
SRP_OUTPUT_INFO = "ClientEncrypt-main"
SRP_INPUT_INFO = "ServerEncrypt-main"

PAIRING_DATA_KEY = "_pd"


def _get_pairing_data(message: Dict[str, object]):
    pairing_data = message.get(PAIRING_DATA_KEY)
    if not pairing_data:
        raise exceptions.AuthenticationError("no pairing data in message")

    if not isinstance(pairing_data, bytes):
        raise exceptions.ProtocolError(
            f"Pairing data has unexpected type: {type(pairing_data)}"
        )

    tlv = read_tlv(pairing_data)
    if TlvValue.Error in tlv:
        raise exceptions.AuthenticationError(stringify(tlv))

    return tlv


class CompanionPairingProcedure:
    """Perform pairing and return new credentials."""

    def __init__(self, protocol, srp: SRPAuthHandler) -> None:
        """Initialize a new CompanionPairingProcedure."""
        self.protocol = protocol
        self.srp = srp
        self._atv_salt = None
        self._atv_pub_key = None

    async def start_pairing(self) -> None:
        """Start pairing procedure."""
        self.srp.initialize()
        await self.protocol.start()

        resp = await self.protocol.exchange_opack(
            FrameType.PS_Start,
            {
                PAIRING_DATA_KEY: hap_tlv8.write_tlv(
                    {TlvValue.Method: b"\x00", TlvValue.SeqNo: b"\x01"}
                ),
                "_pwTy": 1,
            },
        )

        pairing_data = _get_pairing_data(resp)
        self._atv_salt = pairing_data[TlvValue.Salt]
        self._atv_pub_key = pairing_data[TlvValue.PublicKey]
        log_binary(
            _LOGGER,
            "Got pub key and salt",
            Salt=self._atv_salt,
            PubKey=self._atv_pub_key,
        )

    async def finish_pairing(self, pin: int) -> HapCredentials:
        """Finish pairing process."""
        self.srp.step1(pin)

        pub_key, proof = self.srp.step2(self._atv_pub_key, self._atv_salt)

        resp = await self.protocol.exchange_opack(
            FrameType.PS_Next,
            {
                PAIRING_DATA_KEY: hap_tlv8.write_tlv(
                    {
                        TlvValue.SeqNo: b"\x03",
                        TlvValue.PublicKey: pub_key,
                        TlvValue.Proof: proof,
                    }
                ),
                "_pwTy": 1,
            },
        )

        pairing_data = _get_pairing_data(resp)
        atv_proof = pairing_data[TlvValue.Proof]
        log_binary(_LOGGER, "Device", Proof=atv_proof)

        # TODO: Dummy data: what to set? needed at all?
        additional_data = {
            "altIRK": b"-\x54\xe0\x7a\x88*en\x11\xab\x82v-'%\xc5",
            "accountID": "DC6A7CB6-CA1A-4BF4-880D-A61B717814DB",
            "model": "AppleTV6,2",
            "wifiMAC": b"@\xff\xa1\x8f\xa1\xb9",
            "name": "Living Room",
            "mac": b"@\xc4\xff\x8f\xb1\x99",
        }

        encrypted_data = self.srp.step3(
            additional_data={17: opack.pack(additional_data)}
        )

        resp = await self.protocol.exchange_opack(
            FrameType.PS_Next,
            {
                PAIRING_DATA_KEY: hap_tlv8.write_tlv(
                    {
                        TlvValue.SeqNo: b"\x05",
                        TlvValue.EncryptedData: encrypted_data,
                    }
                ),
                "_pwTy": 1,
            },
        )

        pairing_data = _get_pairing_data(resp)
        encrypted_data = pairing_data[TlvValue.EncryptedData]

        return self.srp.step4(encrypted_data)


class CompanionPairingVerifier:
    """Verify credentials and derive new encryption keys."""

    def __init__(
        self, protocol, srp: SRPAuthHandler, credentials: HapCredentials
    ) -> None:
        """Initialize a new CompanionPairingVerifier."""
        self.protocol = protocol
        self.srp = srp
        self.credentials = credentials
        self._output_key = None
        self._input_key = None

    async def verify_credentials(self) -> None:
        """Verify credentials with device."""
        _, public_key = self.srp.initialize()

        resp = await self.protocol.exchange_opack(
            FrameType.PV_Start,
            {
                PAIRING_DATA_KEY: hap_tlv8.write_tlv(
                    {TlvValue.SeqNo: b"\x01", TlvValue.PublicKey: public_key}
                ),
                "_auTy": 4,
            },
        )

        pairing_data = _get_pairing_data(resp)
        server_pub_key = pairing_data[TlvValue.PublicKey]
        encrypted = pairing_data[TlvValue.EncryptedData]
        log_binary(_LOGGER, "Device", Public=self.credentials.ltpk, Encrypted=encrypted)

        encrypted_data = self.srp.verify1(self.credentials, server_pub_key, encrypted)

        await self.protocol.exchange_opack(
            FrameType.PV_Next,
            {
                PAIRING_DATA_KEY: hap_tlv8.write_tlv(
                    {TlvValue.SeqNo: b"\x03", TlvValue.EncryptedData: encrypted_data}
                ),
            },
        )

        # TODO: check status code

        self._output_key, self._input_key = self.srp.verify2(
            SRP_SALT, SRP_OUTPUT_INFO, SRP_INPUT_INFO
        )

    def encryption_keys(self) -> Tuple[str, str]:
        """Return derived encryption keys."""
        if self._output_key is None or self._input_key is None:
            raise exceptions.NoCredentialsError("verification has not succeeded")
        return self._output_key, self._input_key
