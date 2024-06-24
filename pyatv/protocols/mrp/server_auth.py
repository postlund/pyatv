"""MRP server authentication code."""

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
from google.protobuf.message import Message as ProtobufMessage
from srptools import SRPContext, SRPServerSession, constants

from pyatv.auth.hap_srp import hkdf_expand
from pyatv.auth.hap_tlv8 import ErrorCode, TlvValue, read_tlv, write_tlv
from pyatv.auth.server_auth import PIN_CODE, PRIVATE_KEY, SERVER_IDENTIFIER
from pyatv.protocols.mrp import messages, protobuf
from pyatv.support import chacha20, log_binary

_LOGGER = logging.getLogger(__name__)

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


class MrpServerAuth(ABC):
    """Server-side implementation of MRP authentication."""

    def __init__(self, device_name, unique_id=SERVER_IDENTIFIER, pin=PIN_CODE):
        """Initialize a new instance if MrpServerAuth."""
        self.device_name = device_name
        self.unique_id = unique_id.encode()
        self.input_key = None
        self.output_key = None
        self.has_paired = False
        self.keys = generate_keys(PRIVATE_KEY)
        self.session, self.salt = new_server_session(self.keys, str(PIN_CODE))

    def handle_device_info(self, message, _):
        """Handle received device information message."""
        _LOGGER.debug("Received device info message")

        # TODO: Consolidate this better with messages.device_information(...)
        resp = messages.create(
            protobuf.DEVICE_INFO_MESSAGE, identifier=message.identifier
        )
        resp.inner().uniqueIdentifier = self.unique_id
        resp.inner().name = self.device_name
        resp.inner().localizedModelName = self.device_name
        resp.inner().systemBuildVersion = "17K449"
        resp.inner().applicationBundleIdentifier = "com.apple.mediaremoted"
        resp.inner().protocolVersion = 1
        resp.inner().lastSupportedMessageType = 77
        resp.inner().supportsSystemPairing = True
        resp.inner().allowsPairing = True
        resp.inner().systemMediaApplication = "com.apple.TVMusic"
        resp.inner().supportsACL = True
        resp.inner().supportsSharedQueue = True
        resp.inner().supportsExtendedMotion = True
        resp.inner().sharedQueueVersion = 2
        resp.inner().deviceClass = 4
        self.send_to_client(resp)

    def handle_crypto_pairing(self, message, inner):
        """Handle incoming crypto pairing message."""
        _LOGGER.debug("Received crypto pairing message")
        pairing_data = read_tlv(inner.pairingData)
        seqno = pairing_data[TlvValue.SeqNo][0]

        # Work-around for now to support "tries" to auth before pairing
        if seqno == 1:
            if TlvValue.PublicKey in pairing_data:
                self.has_paired = True
            elif TlvValue.Method in pairing_data:
                self.has_paired = False

        suffix = "verify" if self.has_paired else "setup"
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

        chacha = chacha20.Chacha20Cipher8byteNonce(session_key, session_key)
        encrypted = chacha.encrypt(tlv, nonce="PV-Msg02".encode())

        msg = messages.crypto_pairing(
            {
                TlvValue.SeqNo: b"\x02",
                TlvValue.PublicKey: server_pub_key,
                TlvValue.EncryptedData: encrypted,
            }
        )

        self.output_key = hkdf_expand(
            "MediaRemote-Salt", "MediaRemote-Write-Encryption-Key", shared_key
        )

        self.input_key = hkdf_expand(
            "MediaRemote-Salt", "MediaRemote-Read-Encryption-Key", shared_key
        )

        log_binary(_LOGGER, "Keys", Output=self.output_key, Input=self.input_key)
        self.send_to_client(msg)

    def _m3_verify(self, pairing_data):
        self.send_to_client(messages.crypto_pairing({TlvValue.SeqNo: b"\x04"}))
        self.enable_encryption(self.input_key, self.output_key)

    def _m1_setup(self, pairing_data):
        msg = messages.crypto_pairing(
            {
                TlvValue.Salt: binascii.unhexlify(self.salt),
                TlvValue.PublicKey: binascii.unhexlify(self.session.public),
                TlvValue.SeqNo: b"\x02",
            }
        )

        self.send_to_client(msg)

    def _m3_setup(self, pairing_data):
        pubkey = binascii.hexlify(pairing_data[TlvValue.PublicKey]).decode()
        self.session.process(pubkey, self.salt)

        proof = binascii.unhexlify(self.session.key_proof_hash)
        if self.session.verify_proof(binascii.hexlify(pairing_data[TlvValue.Proof])):
            msg = messages.crypto_pairing(
                {TlvValue.Proof: proof, TlvValue.SeqNo: b"\x04"}
            )
        else:
            msg = messages.crypto_pairing(
                {
                    TlvValue.Error: bytes([ErrorCode.Authentication]),
                    TlvValue.SeqNo: b"\x04",
                }
            )

        self.send_to_client(msg)

    def _m5_setup(self, _):
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

        device_info = acc_device_x + self.unique_id + self.keys.auth_pub
        signature = self.keys.sign.sign(device_info)

        tlv = write_tlv(
            {
                TlvValue.Identifier: self.unique_id,
                TlvValue.PublicKey: self.keys.auth_pub,
                TlvValue.Signature: signature,
            }
        )

        chacha = chacha20.Chacha20Cipher8byteNonce(session_key, session_key)
        encrypted = chacha.encrypt(tlv, nonce="PS-Msg06".encode())

        msg = messages.crypto_pairing(
            {TlvValue.SeqNo: b"\x06", TlvValue.EncryptedData: encrypted}
        )
        self.has_paired = True

        self.send_to_client(msg)

    @abstractmethod
    def send_to_client(self, message: ProtobufMessage) -> None:
        """Send data to client device (iOS)."""

    @abstractmethod
    def enable_encryption(self, output_key: bytes, input_key: bytes) -> None:
        """Enable encryption with the specified keys."""
