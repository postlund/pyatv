"""MRP server authentication code."""

import logging
import hashlib
import binascii
from collections import namedtuple

import curve25519
from srptools import (SRPContext, SRPServerSession, constants)
from ed25519.keys import SigningKey

from pyatv.mrp import (chacha20, messages, protobuf, tlv8)
from pyatv.mrp.srp import hkdf_expand
from pyatv.support import log_binary


_LOGGER = logging.getLogger(__name__)

PIN_CODE = 1111
CLIENT_IDENTIFIER = '4D797FD3-3538-427E-A47B-A32FC6CF3A69'
CLIENT_CREDENTIALS = 'e734ea6c2b6257de72355e472aa05a4c487e6b463c029ed306d' + \
    'f2f01b5636b58:3c99faa5484bb424bcb5da34cbf5dec6e755139c3674e39abc4ae8' + \
    '9032c87900:35443739374644332d333533382d343237452d413437422d413332464' + \
    '336434633413639:31393966303461372d613536642d343932312d616139392d6165' + \
    '64653932323964393833'
SERVER_IDENTIFIER = '5D797FD3-3538-427E-A47B-A32FC6CF3A69'

ServerKeys = namedtuple('ServerKeys', 'sign auth auth_pub verify verify_pub')


# This is a hack. When using a constant, e.g. 32 * '\xAA', will be corrupted
# for the second client that connects. Not sure why, but this works...
def seed():
    """Generate a static signing seed."""
    a = b''
    for _ in range(32):
        a += b'\xAA'
    return a


def generate_keys(seed):
    """Generate server encryption keys from seed."""
    signing_key = SigningKey(seed)
    verify_private = curve25519.Private(secret=seed)
    return ServerKeys(
        sign=signing_key,
        auth=signing_key.to_bytes(),
        auth_pub=signing_key.get_verifying_key().to_bytes(),
        verify=verify_private,
        verify_pub=verify_private.get_public())


def new_server_session(keys, pin):
    """Create SRP server session."""
    context = SRPContext(
        'Pair-Setup', str(pin),
        prime=constants.PRIME_3072,
        generator=constants.PRIME_3072_GEN,
        hash_func=hashlib.sha512,
        bits_salt=128)
    username, verifier, salt = context.get_user_data_triplet()

    context_server = SRPContext(
        username,
        prime=constants.PRIME_3072,
        generator=constants.PRIME_3072_GEN,
        hash_func=hashlib.sha512,
        bits_salt=128)

    session = SRPServerSession(
        context_server,
        verifier,
        binascii.hexlify(keys.auth).decode())

    return session, salt


class MrpServerAuth:
    """Server-side implementation of MRP authentication."""

    def __init__(self, delegate, device_name,
                 unique_id=SERVER_IDENTIFIER, pin=PIN_CODE):
        """Initialize a new instance if MrpServerAuth."""
        self.delegate = delegate
        self.device_name = device_name
        self.unique_id = unique_id.encode()
        self.input_key = None
        self.output_key = None
        self.has_paired = False
        self.keys = generate_keys(seed())
        self.session, self.salt = new_server_session(self.keys, str(PIN_CODE))

    def handle_device_info(self, message, _):
        """Handle received device information message."""
        _LOGGER.debug('Received device info message')

        # TODO: Consolidate this better with messages.device_information(...)
        resp = messages.create(
            protobuf.DEVICE_INFO_MESSAGE, identifier=message.identifier)
        resp.inner().uniqueIdentifier = self.unique_id
        resp.inner().name = self.device_name
        resp.inner().localizedModelName = self.device_name
        resp.inner().systemBuildVersion = '17K449'
        resp.inner().applicationBundleIdentifier = 'com.apple.mediaremoted'
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
        _LOGGER.debug('Received crypto pairing message')
        pairing_data = tlv8.read_tlv(inner.pairingData)
        seqno = pairing_data[tlv8.TLV_SEQ_NO][0]

        # Work-around for now to support "tries" to auth before pairing
        if seqno == 1:
            if tlv8.TLV_PUBLIC_KEY in pairing_data:
                self.has_paired = True
            elif tlv8.TLV_METHOD in pairing_data:
                self.has_paired = False

        suffix = 'paired' if self.has_paired else 'pairing'
        method = '_seqno{0}_{1}'.format(seqno, suffix)
        getattr(self, method)(pairing_data)

    def _seqno1_paired(self, pairing_data):
        server_pub_key = self.keys.verify_pub.serialize()
        client_pub_key = pairing_data[tlv8.TLV_PUBLIC_KEY]

        shared_key = self.keys.verify.get_shared_key(
            curve25519.Public(client_pub_key), hashfunc=lambda x: x)

        session_key = hkdf_expand('Pair-Verify-Encrypt-Salt',
                                  'Pair-Verify-Encrypt-Info',
                                  shared_key)

        info = server_pub_key + self.unique_id + client_pub_key
        signature = self.keys.sign.sign(info)

        tlv = tlv8.write_tlv({
            tlv8.TLV_IDENTIFIER: self.unique_id,
            tlv8.TLV_SIGNATURE: signature
        })

        chacha = chacha20.Chacha20Cipher(session_key, session_key)
        encrypted = chacha.encrypt(tlv, nounce='PV-Msg02'.encode())

        msg = messages.crypto_pairing({
            tlv8.TLV_SEQ_NO: b'\x02',
            tlv8.TLV_PUBLIC_KEY: server_pub_key,
            tlv8.TLV_ENCRYPTED_DATA: encrypted
        })

        self.output_key = hkdf_expand('MediaRemote-Salt',
                                      'MediaRemote-Write-Encryption-Key',
                                      shared_key)

        self.input_key = hkdf_expand('MediaRemote-Salt',
                                     'MediaRemote-Read-Encryption-Key',
                                     shared_key)

        log_binary(_LOGGER,
                   'Keys',
                   Output=self.output_key,
                   Input=self.input_key)
        self.delegate.send(msg)

    def _seqno1_pairing(self, pairing_data):
        msg = messages.crypto_pairing({
            tlv8.TLV_SALT: binascii.unhexlify(self.salt),
            tlv8.TLV_PUBLIC_KEY: binascii.unhexlify(self.session.public),
            tlv8.TLV_SEQ_NO: b'\x02'
        })

        self.delegate.send(msg)

    def _seqno3_paired(self, pairing_data):
        self.delegate.send(messages.crypto_pairing({tlv8.TLV_SEQ_NO: b'\x04'}))
        self.delegate.enable_encryption(self.input_key, self.output_key)

    def _seqno3_pairing(self, pairing_data):
        pubkey = binascii.hexlify(
            pairing_data[tlv8.TLV_PUBLIC_KEY]).decode()
        self.session.process(pubkey, self.salt)

        proof = binascii.unhexlify(self.session.key_proof_hash)
        if self.session.verify_proof(
                binascii.hexlify(pairing_data[tlv8.TLV_PROOF])):

            msg = messages.crypto_pairing({
                tlv8.TLV_PROOF: proof,
                tlv8.TLV_SEQ_NO: b'\x04'
            })
        else:
            msg = messages.crypto_pairing({
                tlv8.TLV_ERROR: tlv8.ERROR_AUTHENTICATION.encode(),
                tlv8.TLV_SEQ_NO: b'\x04'
            })

        self.delegate.send(msg)

    def _seqno5_pairing(self, _):
        session_key = hkdf_expand(
            'Pair-Setup-Encrypt-Salt',
            'Pair-Setup-Encrypt-Info',
            binascii.unhexlify(self.session.key))

        acc_device_x = hkdf_expand(
            'Pair-Setup-Accessory-Sign-Salt',
            'Pair-Setup-Accessory-Sign-Info',
            binascii.unhexlify(self.session.key))

        device_info = acc_device_x + self.unique_id + self.keys.auth_pub
        signature = self.keys.sign.sign(device_info)

        tlv = tlv8.write_tlv({tlv8.TLV_IDENTIFIER: self.unique_id,
                              tlv8.TLV_PUBLIC_KEY: self.keys.auth_pub,
                              tlv8.TLV_SIGNATURE: signature})

        chacha = chacha20.Chacha20Cipher(session_key, session_key)
        encrypted = chacha.encrypt(tlv, nounce='PS-Msg06'.encode())

        msg = messages.crypto_pairing({
            tlv8.TLV_SEQ_NO: b'\x06',
            tlv8.TLV_ENCRYPTED_DATA: encrypted,
        })
        self.has_paired = True

        self.delegate.send(msg)
