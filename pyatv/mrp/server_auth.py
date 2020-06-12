"""MRP server authentication code."""

import logging
import hashlib
import binascii
from collections import namedtuple

from srptools import SRPContext, SRPServerSession, constants
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.asymmetric.x25519 import (
    X25519PrivateKey,
    X25519PublicKey,
)

from pyatv.mrp import chacha20, messages, protobuf
from pyatv.mrp.srp import hkdf_expand
from pyatv.support import log_binary
from pyatv.support.hap_tlv8 import TlvValue, ErrorCode, read_tlv, write_tlv

_LOGGER = logging.getLogger(__name__)

PIN_CODE = 1111
CLIENT_IDENTIFIER = "4D797FD3-3538-427E-A47B-A32FC6CF3A69"
CLIENT_CREDENTIALS = (
    "e734ea6c2b6257de72355e472aa05a4c487e6b463c029ed306d"
    + "f2f01b5636b58:3c99faa5484bb424bcb5da34cbf5dec6e755139c3674e39abc4ae8"
    + "9032c87900:35443739374644332d333533382d343237452d413437422d413332464"
    + "336434633413639:31393966303461372d613536642d343932312d616139392d6165"
    + "64653932323964393833"
)
SERVER_IDENTIFIER = "5D797FD3-3538-427E-A47B-A32FC6CF3A69"
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


class MrpServerAuth:
    """Server-side implementation of MRP authentication."""

    def __init__(
        self, delegate, device_name, unique_id=SERVER_IDENTIFIER, pin=PIN_CODE
    ):
        """Initialize a new instance if MrpServerAuth."""
        self.delegate = delegate
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
        self.delegate.send(resp)

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

        suffix = "paired" if self.has_paired else "pairing"
        method = "_seqno{0}_{1}".format(seqno, suffix)
        getattr(self, method)(pairing_data)

    def _seqno1_paired(self, pairing_data):
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
        self.delegate.send(msg)

    def _seqno1_pairing(self, pairing_data):
        msg = messages.crypto_pairing(
            {
                TlvValue.Salt: binascii.unhexlify(self.salt),
                TlvValue.PublicKey: binascii.unhexlify(self.session.public),
                TlvValue.SeqNo: b"\x02",
            }
        )

        self.delegate.send(msg)

    def _seqno3_paired(self, pairing_data):
        self.delegate.send(messages.crypto_pairing({TlvValue.SeqNo: b"\x04"}))
        self.delegate.enable_encryption(self.input_key, self.output_key)

    def _seqno3_pairing(self, pairing_data):
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

        self.delegate.send(msg)

    def _seqno5_pairing(self, _):
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

        chacha = chacha20.Chacha20Cipher(session_key, session_key)
        encrypted = chacha.encrypt(tlv, nounce="PS-Msg06".encode())

        msg = messages.crypto_pairing(
            {TlvValue.SeqNo: b"\x06", TlvValue.EncryptedData: encrypted}
        )
        self.has_paired = True

        self.delegate.send(msg)
