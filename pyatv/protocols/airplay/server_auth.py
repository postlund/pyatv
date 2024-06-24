"""AirPlay server authentication code.

NB: Only supports transient pairing used by some AirPlay 2 devices.
"""

from abc import ABC, abstractmethod
import binascii
from collections import namedtuple
import hashlib
import logging
import plistlib
from typing import Optional, Tuple

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.asymmetric.x25519 import (
    X25519PrivateKey,
    X25519PublicKey,
)
from srptools import SRPContext, SRPServerSession, constants

from pyatv.auth.hap_srp import hkdf_expand
from pyatv.auth.hap_tlv8 import ErrorCode, TlvValue, read_tlv, write_tlv
from pyatv.auth.server_auth import PIN_CODE, PRIVATE_KEY, SERVER_IDENTIFIER
from pyatv.protocols.airplay.auth.hap_transient import TRANSIENT_PIN
from pyatv.support import chacha20, http, log_binary

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


def new_server_session(keys, pin) -> Tuple[SRPServerSession, bytes]:
    """Create SRP server session."""
    context = SRPContext(
        "Pair-Setup",
        str(pin),
        prime=constants.PRIME_3072,
        generator=constants.PRIME_3072_GEN,
        hash_func=hashlib.sha512,
        bits_salt=128,
        bits_random=512,
    )
    username, verifier, salt = context.get_user_data_triplet()

    context_server = SRPContext(
        username,
        prime=constants.PRIME_3072,
        generator=constants.PRIME_3072_GEN,
        hash_func=hashlib.sha512,
        bits_salt=128,
        bits_random=512,
    )

    session = SRPServerSession(
        context_server, verifier, binascii.hexlify(keys.auth).decode()
    )

    return session, salt


class PlayFair:
    """Basic support for FairPlay authentication."""

    MODES = 4
    MODE_POSITON = 14
    TYPE_POSITION = 5
    SEQ_POSITION = 6
    SETUP_MESSAGE_TYPE = 1
    DECRYPT_MESSAGE_TYPE = 2
    SETUP1_MESSAGE_SEQ = 1
    SETUP2_MESSAGE_SEQ = 3
    SETUP1_RESPONSE_LENGTH = 142
    SETUP2_RESPONSE_LENGTH = 32
    SETUP2_RESPONSE_SUFFIX_LENGTH = 20

    # pylint: disable=line-too-long
    reply_message = [
        b"\x46\x50\x4c\x59\x03\x01\x02\x00\x00\x00\x00\x82\x02\x00\x0f\x9f\x3f\x9e\x0a\x25\x21\xdb\xdf\x31\x2a\xb2\xbf\xb2\x9e\x8d\x23\x2b\x63\x76\xa8\xc8\x18\x70\x1d\x22\xae\x93\xd8\x27\x37\xfe\xaf\x9d\xb4\xfd\xf4\x1c\x2d\xba\x9d\x1f\x49\xca\xaa\xbf\x65\x91\xac\x1f\x7b\xc6\xf7\xe0\x66\x3d\x21\xaf\xe0\x15\x65\x95\x3e\xab\x81\xf4\x18\xce\xed\x09\x5a\xdb\x7c\x3d\x0e\x25\x49\x09\xa7\x98\x31\xd4\x9c\x39\x82\x97\x34\x34\xfa\xcb\x42\xc6\x3a\x1c\xd9\x11\xa6\xfe\x94\x1a\x8a\x6d\x4a\x74\x3b\x46\xc3\xa7\x64\x9e\x44\xc7\x89\x55\xe4\x9d\x81\x55\x00\x95\x49\xc4\xe2\xf7\xa3\xf6\xd5\xba",  # noqa
        b"\x46\x50\x4c\x59\x03\x01\x02\x00\x00\x00\x00\x82\x02\x01\xcf\x32\xa2\x57\x14\xb2\x52\x4f\x8a\xa0\xad\x7a\xf1\x64\xe3\x7b\xcf\x44\x24\xe2\x00\x04\x7e\xfc\x0a\xd6\x7a\xfc\xd9\x5d\xed\x1c\x27\x30\xbb\x59\x1b\x96\x2e\xd6\x3a\x9c\x4d\xed\x88\xba\x8f\xc7\x8d\xe6\x4d\x91\xcc\xfd\x5c\x7b\x56\xda\x88\xe3\x1f\x5c\xce\xaf\xc7\x43\x19\x95\xa0\x16\x65\xa5\x4e\x19\x39\xd2\x5b\x94\xdb\x64\xb9\xe4\x5d\x8d\x06\x3e\x1e\x6a\xf0\x7e\x96\x56\x16\x2b\x0e\xfa\x40\x42\x75\xea\x5a\x44\xd9\x59\x1c\x72\x56\xb9\xfb\xe6\x51\x38\x98\xb8\x02\x27\x72\x19\x88\x57\x16\x50\x94\x2a\xd9\x46\x68\x8a",  # noqa
        b"\x46\x50\x4c\x59\x03\x01\x02\x00\x00\x00\x00\x82\x02\x02\xc1\x69\xa3\x52\xee\xed\x35\xb1\x8c\xdd\x9c\x58\xd6\x4f\x16\xc1\x51\x9a\x89\xeb\x53\x17\xbd\x0d\x43\x36\xcd\x68\xf6\x38\xff\x9d\x01\x6a\x5b\x52\xb7\xfa\x92\x16\xb2\xb6\x54\x82\xc7\x84\x44\x11\x81\x21\xa2\xc7\xfe\xd8\x3d\xb7\x11\x9e\x91\x82\xaa\xd7\xd1\x8c\x70\x63\xe2\xa4\x57\x55\x59\x10\xaf\x9e\x0e\xfc\x76\x34\x7d\x16\x40\x43\x80\x7f\x58\x1e\xe4\xfb\xe4\x2c\xa9\xde\xdc\x1b\x5e\xb2\xa3\xaa\x3d\x2e\xcd\x59\xe7\xee\xe7\x0b\x36\x29\xf2\x2a\xfd\x16\x1d\x87\x73\x53\xdd\xb9\x9a\xdc\x8e\x07\x00\x6e\x56\xf8\x50\xce",  # noqa
        b"\x46\x50\x4c\x59\x03\x01\x02\x00\x00\x00\x00\x82\x02\x03\x90\x01\xe1\x72\x7e\x0f\x57\xf9\xf5\x88\x0d\xb1\x04\xa6\x25\x7a\x23\xf5\xcf\xff\x1a\xbb\xe1\xe9\x30\x45\x25\x1a\xfb\x97\xeb\x9f\xc0\x01\x1e\xbe\x0f\x3a\x81\xdf\x5b\x69\x1d\x76\xac\xb2\xf7\xa5\xc7\x08\xe3\xd3\x28\xf5\x6b\xb3\x9d\xbd\xe5\xf2\x9c\x8a\x17\xf4\x81\x48\x7e\x3a\xe8\x63\xc6\x78\x32\x54\x22\xe6\xf7\x8e\x16\x6d\x18\xaa\x7f\xd6\x36\x25\x8b\xce\x28\x72\x6f\x66\x1f\x73\x88\x93\xce\x44\x31\x1e\x4b\xe6\xc0\x53\x51\x93\xe5\xef\x72\xe8\x68\x62\x33\x72\x9c\x22\x7d\x82\x0c\x99\x94\x45\xd8\x92\x46\xc8\xc3\x59",  # noqa
    ]
    # pylint: enable=line-too-long

    fp_header = b"\x46\x50\x4c\x59\x03\x01\x04\x00\x00\x00\x00\x14"

    def fairplay_setup(self, request):
        """Generate response to FairPlay request."""
        if request[4] != 3:
            # Unsupported fairplay version
            return -1

        msg_type = request[self.TYPE_POSITION]
        seq = request[self.SEQ_POSITION]
        # fp.keymsglen = 0;

        if msg_type == self.SETUP_MESSAGE_TYPE:
            if seq == self.SETUP1_MESSAGE_SEQ:
                mode = request[self.MODE_POSITON]
                response = self.reply_message[mode]
            elif seq == self.SETUP2_MESSAGE_SEQ:
                response = self.fp_header
                response = (
                    response
                    + request[
                        len(request) - self.SETUP2_RESPONSE_SUFFIX_LENGTH : len(request)
                    ]
                )
            return response
        return None


class BaseAirPlayServerAuth(http.HttpSimpleRouter, ABC):
    """Shared part of server-side implementation of AirPlay authentication."""

    keys = generate_keys(PRIVATE_KEY)

    def __init__(self, name: str, unique_id=SERVER_IDENTIFIER, pin: int = PIN_CODE):
        """Initialize a new instance if BaseAirPlayServerAuth."""
        super().__init__()
        self.name = name
        self.unique_id = unique_id.encode()
        self.pin = pin
        self.session: Optional[SRPServerSession] = None
        self.salt: Optional[bytes] = None
        self.shared_key: Optional[bytes] = None
        self.input_key: Optional[bytes] = None
        self.output_key: Optional[bytes] = None
        self.add_route("POST", "^/pair-pin-start$", self.handle_pair_pin_start)
        self.add_route("POST", "^/pair-setup$", self.handle_pair_setup)
        self.add_route("POST", "^/pair-verify$", self.handle_pair_verify)

    def handle_pair_pin_start(self, request: http.HttpRequest):
        """Handle incoming /pair-pin-start request."""
        return http.HttpResponse(
            request.protocol,
            request.version,
            200,
            "OK",
            {"CSeq": request.headers.get("CSeq", "1")},
            b"",
        )

    def handle_pair_setup(self, request: http.HttpRequest):
        """Handle incoming /pair-setup request."""
        auth_version = request.headers.get("X-Apple-HKP")
        if auth_version == "3":
            return self.handle_pair_setup_hap(request)
        if auth_version == "4":
            return self.handle_pair_setup_hap_transient(request)
        return http.HttpResponse(
            request.protocol,
            request.version,
            501,
            "Not implemented",
            {"CSeq": request.headers.get("CSeq", "1")},
            b"",
        )

    def handle_pair_setup_hap(self, request: http.HttpRequest):
        """Handle incoming HAP /pair-setup request."""
        body = (
            request.body
            if isinstance(request.body, bytes)
            else request.body.encode("utf-8")
        )
        pairing_data = read_tlv(body)
        _LOGGER.debug("Pair-setup message received: %s", pairing_data)

        seqno = int.from_bytes(pairing_data[TlvValue.SeqNo], byteorder="little")
        tlv = getattr(self, f"_m{seqno}_setup".format(seqno))(
            pairing_data, transient=False
        )
        return http.HttpResponse(
            request.protocol,
            request.version,
            200,
            "OK",
            {
                "CSeq": request.headers.get("CSeq", "1"),
                "Content-Type": "application/x-apple-binary-plist",
            },
            tlv,
        )

    def handle_pair_setup_hap_transient(self, request: http.HttpRequest):
        """Handle incoming HAP transient /pair-setup request."""
        body = (
            request.body
            if isinstance(request.body, bytes)
            else request.body.encode("utf-8")
        )
        pairing_data = read_tlv(body)
        _LOGGER.debug("Transient pair-setup message received: %s", pairing_data)

        seqno = int.from_bytes(pairing_data[TlvValue.SeqNo], byteorder="little")
        tlv = getattr(self, f"_m{seqno}_setup".format(seqno))(
            pairing_data, transient=True
        )
        return http.HttpResponse(
            request.protocol,
            request.version,
            200,
            "OK",
            {
                "CSeq": request.headers.get("CSeq", "1"),
                "Content-Type": "application/x-apple-binary-plist",
            },
            tlv,
        )

    def handle_pair_verify(self, request: http.HttpRequest):
        """Handle incoming /pair-verify request."""
        if request.headers.get("X-Apple-HKP") != "3":
            return http.HttpResponse(
                request.protocol,
                request.version,
                501,
                "Not implemented",
                {"CSeq": request.headers.get("CSeq", "1")},
                b"",
            )

        body = (
            request.body
            if isinstance(request.body, bytes)
            else request.body.encode("utf-8")
        )
        pairing_data = read_tlv(body)
        _LOGGER.debug("Pair-verify message received: %s", pairing_data)

        seqno = pairing_data[TlvValue.SeqNo][0]
        tlv = getattr(self, f"_m{seqno}_verify")(pairing_data)
        return http.HttpResponse(
            request.protocol,
            request.version,
            200,
            "OK",
            {
                "CSeq": request.headers.get("CSeq", "1"),
                "Content-Type": "application/octet-stream",
            },
            tlv,
        )

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

        tlv = {
            TlvValue.SeqNo: b"\x02",
            TlvValue.PublicKey: server_pub_key,
            TlvValue.EncryptedData: encrypted,
        }

        self.shared_key = shared_key
        self.input_key = hkdf_expand(
            "Control-Salt", "Control-Write-Encryption-Key", shared_key
        )
        self.output_key = hkdf_expand(
            "Control-Salt", "Control-Read-Encryption-Key", shared_key
        )

        log_binary(_LOGGER, "Keys", Output=self.output_key, Input=self.input_key)
        return write_tlv(tlv)

    def _m3_verify(self, pairing_data):
        self.enable_encryption(self.output_key, self.input_key)
        return write_tlv({TlvValue.SeqNo: b"\x04"})

    def _m1_setup(self, pairing_data, transient: bool):
        self.session, self.salt = new_server_session(
            self.keys, str(TRANSIENT_PIN if transient else self.pin)
        )

        return write_tlv(
            {
                TlvValue.SeqNo: b"\x02",
                TlvValue.Salt: binascii.unhexlify(self.salt),
                TlvValue.PublicKey: binascii.unhexlify(self.session.public),
            }
        )

    def _m3_setup(self, pairing_data, transient: bool):
        assert self.session is not None
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

        if transient:
            self.shared_key = binascii.unhexlify(self.session.key)
            self.input_key = hkdf_expand(
                "Control-Salt",
                "Control-Write-Encryption-Key",
                self.shared_key,
            )
            self.output_key = hkdf_expand(
                "Control-Salt",
                "Control-Read-Encryption-Key",
                self.shared_key,
            )

            self.enable_encryption(self.output_key, self.input_key)
            self.has_paired()

        return write_tlv(tlv)

    def _m5_setup(self, pairing_data, transient: bool):
        assert self.session is not None

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

        chacha = chacha20.Chacha20Cipher8byteNonce(session_key, session_key)
        decrypted_tlv_bytes = chacha.decrypt(
            pairing_data[TlvValue.EncryptedData], nonce="PS-Msg05".encode()
        )

        _LOGGER.debug("MSG5 EncryptedData=%s", read_tlv(decrypted_tlv_bytes))

        # other = {
        #     "altIRK": b"-\x54\xe0\x7a\x88*en\x11\xab\x82v-'%\xc5",
        #     "accountID": "DC6A7CB6-CA1A-4BF4-880D-A61B717814DB",
        #     "model": "AppleTV6,2",
        #     "wifiMAC": b"@\xff\xa1\x8f\xa1\xb9",
        #     "name": "Living Room",
        #     "mac": b"@\xc4\xff\x8f\xb1\x99",
        # }

        device_info = acc_device_x + self.unique_id + self.keys.auth_pub
        signature = self.keys.sign.sign(device_info)

        tlv = write_tlv(
            {
                TlvValue.Identifier: self.unique_id,
                TlvValue.PublicKey: self.keys.auth_pub,
                TlvValue.Signature: signature,
                # 17: opack.pack(other),
            }
        )

        chacha = chacha20.Chacha20Cipher8byteNonce(session_key, session_key)
        encrypted = chacha.encrypt(tlv, nonce="PS-Msg06".encode())

        self.has_paired()
        return write_tlv({TlvValue.SeqNo: b"\x06", TlvValue.EncryptedData: encrypted})

    @abstractmethod
    def enable_encryption(self, output_key: bytes, input_key: bytes) -> None:
        """Enable encryption with the specified keys."""

    @staticmethod
    def has_paired():
        """Call when a client has paired."""


class AirPlayServerAuth(BaseAirPlayServerAuth, ABC):
    """Server-side implementation of AirPlay authentication."""

    def __init__(self, name: str, unique_id=SERVER_IDENTIFIER, pin: int = PIN_CODE):
        """Initialize a new instance if AirPlayServerAuth."""
        super().__init__(name, unique_id, pin)
        self.add_route("GET", "^/info$", self.handle_info)
        self.add_route("OPTIONS", ".*", self.handle_options)
        self.add_route("POST", "^/fp-setup$", self.handle_fp_setup)

    def handle_options(self, request: http.HttpRequest):
        """Handle incoming OPTIONS request."""
        return http.HttpResponse(
            request.protocol,
            request.version,
            200,
            "OK",
            {"CSeq": request.headers["CSeq"], "Public": ", ".join(self._routes.keys())},
            b"",
        )

    @staticmethod
    def handle_fp_setup(request):
        """Handle request to set up FairPlay."""
        response = PlayFair().fairplay_setup(request.body)
        return http.HttpResponse(
            request.protocol,
            request.version,
            200,
            "OK",
            {"CSeq": request.headers["CSeq"]},
            response,
        )

    def handle_info(self, request: http.HttpRequest):
        """Handle incoming /info request."""
        _LOGGER.debug("Sending AirPlay device info")
        body = {
            "psi": "dc0eccfd-f834-47d5-95ce-d8f41e2544f6",
            "vv": 2,
            "playbackCapabilities": {
                "supportsInterstitials": False,
                "supportsFPSSecureStop": False,
                "supportsUIForAudioOnlyContent": False,
            },
            "canRecordScreenStream": False,
            "statusFlags": 4,
            "keepAliveSendStatsAsBody": True,
            "protocolVersion": "1.1",
            "volumeControlType": 3,
            "name": self.name,
            "senderAddress": "10.0.10.254:45285",  # TODO: correct address here
            "deviceID": "ff:ee:dd:cc:bb:aa",
            "pi": "a1023589-a2ef-47de-8596-42f6fe5caacd",
            "screenDemoMode": False,
            "initialVolume": -27.0,
            "featuresEx": "AMp/StBrbbb",
            "supportedFormats": {
                "lowLatencyAudioStream": 4398080065536,
                "screenStream": 21235712,
                "audioStream": 21235712,
                "bufferStream": 1649282121728,
            },
            "sourceVersion": "550.10",
            "model": "AudioAccessory5,1",
            "pk": 32 * b"ab",
            "macAddress": "ff:ee:dd:cc:bb:aa",
            "receiverHDRCapability": "4k60",
            "features": "0x4A7FCA00,0x3C356BD0",
        }

        return http.HttpResponse(
            "RTSP",
            "1.0",
            200,
            "OK",
            {"CSeq": request.headers["CSeq"]},
            plistlib.dumps(body),
        )
