"""Companion+ server authentication code."""

from abc import ABC, abstractmethod
import binascii
from collections import namedtuple
import hashlib
import logging

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.asymmetric.x25519 import (
    X25519PrivateKey,
    X25519PublicKey,
)
from srptools import SRPContext, SRPServerSession, constants

from pyatv.auth.hap_srp import hkdf_expand
from pyatv.auth.hap_tlv8 import ErrorCode, TlvValue, read_tlv, write_tlv
from pyatv.protocols.companion import opack
from pyatv.protocols.companion.connection import FrameType
from pyatv.support import chacha20, log_binary

_LOGGER = logging.getLogger(__name__)

PIN_CODE = 1111
CLIENT_CREDENTIALS = (
    "E734EA6C2B6257DE72355E472AA05A4C487E6B463C029ED306DF2F01B5636B58:"
    + "80FD8265B0748DA90BC5C5294DABE394D3D47199994AE96AC73EE45C783537B1:"
    + "35443739374644332D333533382D343237452D413437422D41333246433643463"
    + "3413641:61343333373865362D613438612D343766382D613931632D666465366"
    + "165316532643233"
)

SERVER_IDENTIFIER = "5D797FD3-3538-427E-A47B-A32FC6CF3A6A"
PRIVATE_KEY = 32 * b"\xAA"

ServerKeys = namedtuple("ServerKeys", "sign auth auth_pub verify verify_pub")


def generate_keys(seed):
    """Generate server encryption keys from seed."""
    signing_key = Ed25519PrivateKey.from_private_bytes(seed)
    verify_private = X25519PrivateKey.from_private_bytes(seed)
    return ServerKeys(
        sign=signing_key,
        auth=signing_key.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption(),
        ),
        auth_pub=signing_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
        ),
        verify=verify_private,
        verify_pub=verify_private.public_key(),
    )


def new_server_session(keys, pin):
    """Create SRP server session."""
    context = SRPContext(
        "Pair-Setup",
        str(pin),
        prime=constants.PRIME_3072,
        generator=constants.PRIME_3072_GEN,
        hash_func=hashlib.sha512,
        bits_salt=128,
    )
    username, verifier, salt = context.get_user_data_triplet()

    context_server = SRPContext(
        username,
        prime=constants.PRIME_3072,
        generator=constants.PRIME_3072_GEN,
        hash_func=hashlib.sha512,
        bits_salt=128,
    )

    session = SRPServerSession(
        context_server, verifier, binascii.hexlify(keys.auth).decode()
    )

    return session, salt


class CompanionServerAuth(ABC):
    """Server-side implementation of Companion authentication."""

    def __init__(self, device_name, unique_id=SERVER_IDENTIFIER, pin=PIN_CODE):
        """Initialize a new instance if CompanionServerAuth."""
        self.device_name = device_name
        self.unique_id = unique_id.encode()
        self.input_key = None
        self.output_key = None
        self.keys = generate_keys(PRIVATE_KEY)
        self.session, self.salt = new_server_session(self.keys, str(PIN_CODE))

    def handle_auth_frame(self, frame_type, data):
        """Handle incoming auth message."""
        _LOGGER.debug("Received auth frame: type=%s, data=%s", frame_type, data)
        pairing_data = read_tlv(data["_pd"])
        seqno = int.from_bytes(pairing_data[TlvValue.SeqNo], byteorder="little")

        suffix = (
            "verify"
            if frame_type in [FrameType.PV_Start, FrameType.PV_Next]
            else "setup"
        )
        getattr(self, f"_m{seqno}_{suffix}")(pairing_data)

    def _m1_verify(self, pairing_data):
        server_pub_key = self.keys.verify_pub.public_bytes(
            encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
        )
        client_pub_key = pairing_data[TlvValue.PublicKey]

        shared_key = self.keys.verify.exchange(
            X25519PublicKey.from_public_bytes(client_pub_key)
        )

        session_key = hkdf_expand(
            "Pair-Verify-Encrypt-Salt", "Pair-Verify-Encrypt-Info", shared_key
        )

        info = server_pub_key + self.unique_id + client_pub_key
        signature = self.keys.sign.sign(info)

        tlv = write_tlv(
            {TlvValue.Identifier: self.unique_id, TlvValue.Signature: signature}
        )

        chacha = chacha20.Chacha20Cipher(session_key, session_key)
        encrypted = chacha.encrypt(tlv, nounce="PV-Msg02".encode())

        tlv = write_tlv(
            {
                TlvValue.SeqNo: b"\x02",
                TlvValue.PublicKey: server_pub_key,
                TlvValue.EncryptedData: encrypted,
            }
        )

        self.output_key = hkdf_expand("", "ServerEncrypt-main", shared_key)
        self.input_key = hkdf_expand("", "ClientEncrypt-main", shared_key)

        log_binary(_LOGGER, "Keys", Output=self.output_key, Input=self.input_key)

        self.send_to_client(FrameType.PV_Next, {"_pd": tlv})

    def _m3_verify(self, pairing_data):
        self.send_to_client(
            FrameType.PV_Next, {"_pd": write_tlv({TlvValue.SeqNo: b"\x04"})}
        )
        self.enable_encryption(self.output_key, self.input_key)

    def _m1_setup(self, pairing_data):
        tlv = write_tlv(
            {
                TlvValue.SeqNo: b"\x02",
                TlvValue.Salt: binascii.unhexlify(self.salt),
                TlvValue.PublicKey: binascii.unhexlify(self.session.public),
                27: b"\x01",
            }
        )
        self.send_to_client(FrameType.PS_Next, {"_pd": tlv, "_pwTy": 1})

    def _m3_setup(self, pairing_data):
        pubkey = binascii.hexlify(pairing_data[TlvValue.PublicKey]).decode()
        self.session.process(pubkey, self.salt)

        if self.session.verify_proof(binascii.hexlify(pairing_data[TlvValue.Proof])):
            proof = binascii.unhexlify(self.session.key_proof_hash)
            tlv = {TlvValue.Proof: proof, TlvValue.SeqNo: b"\x04"}
        else:
            tlv = {
                TlvValue.Error: bytes([ErrorCode.Authentication]),
                TlvValue.SeqNo: b"\x04",
            }

        self.send_to_client(FrameType.PS_Next, {"_pd": write_tlv(tlv)})

    def _m5_setup(self, pairing_data):
        session_key = hkdf_expand(
            "Pair-Setup-Encrypt-Salt",
            "Pair-Setup-Encrypt-Info",
            binascii.unhexlify(self.session.key),
        )

        acc_device_x = hkdf_expand(
            "Pair-Setup-Accessory-Sign-Salt",
            "Pair-Setup-Accessory-Sign-Info",
            binascii.unhexlify(self.session.key),
        )

        chacha = chacha20.Chacha20Cipher(session_key, session_key)
        decrypted_tlv_bytes = chacha.decrypt(
            pairing_data[TlvValue.EncryptedData], nounce="PS-Msg05".encode()
        )

        _LOGGER.debug("MSG5 EncryptedData=%s", read_tlv(decrypted_tlv_bytes))

        other = {
            "altIRK": b"-\x54\xe0\x7a\x88*en\x11\xab\x82v-'%\xc5",
            "accountID": "DC6A7CB6-CA1A-4BF4-880D-A61B717814DB",
            "model": "AppleTV6,2",
            "wifiMAC": b"@\xff\xa1\x8f\xa1\xb9",
            "name": "Living Room",
            "mac": b"@\xc4\xff\x8f\xb1\x99",
        }

        device_info = acc_device_x + self.unique_id + self.keys.auth_pub
        signature = self.keys.sign.sign(device_info)

        tlv = {
            TlvValue.Identifier: self.unique_id,
            TlvValue.PublicKey: self.keys.auth_pub,
            TlvValue.Signature: signature,
            17: opack.pack(other),
        }

        tlv = write_tlv(tlv)

        chacha = chacha20.Chacha20Cipher(session_key, session_key)
        encrypted = chacha.encrypt(tlv, nounce="PS-Msg06".encode())

        tlv = write_tlv({TlvValue.SeqNo: b"\x06", TlvValue.EncryptedData: encrypted})

        self.send_to_client(FrameType.PS_Next, {"_pd": tlv})
        self.has_paired()

    @abstractmethod
    def send_to_client(self, frame_type: FrameType, data: object) -> None:
        """Send data to client device (iOS)."""

    @abstractmethod
    def enable_encryption(self, output_key: bytes, input_key: bytes) -> None:
        """Enable encryption with the specified keys."""

    @staticmethod
    def has_paired():
        """Call when a client has paired."""
