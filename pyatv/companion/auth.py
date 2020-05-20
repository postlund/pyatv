"""Device pairing and derivation of encryption keys.

THIS IS PROTOTYPE AND DOES NOT WORK!
"""

import logging
from enum import Enum
from collections import namedtuple

from pyatv.companion import opack
from pyatv.support import log_binary, hap_tlv8

_LOGGER = logging.getLogger(__name__)

Frame = namedtuple("Frame", "type data")


class FrameType(Enum):
    """Frame type values."""

    Unknown = 0
    NoOp = 1
    PS_Start = 3
    PS_Next = 4
    PV_Start = 5
    PV_Next = 6
    U_OPACK = 7
    E_OPACK = 8
    P_OPACK = 9
    PA_Req = 10
    PA_Rsp = 11
    SessionStartRequest = 16
    SessionStartResponse = 17
    SessionData = 18
    FamilyIdentityRequest = 32
    FamilyIdentityResponse = 33
    FamilyIdentityUpdate = 34


def decode_frame(data: bytes):
    """Decode a frame from bytes."""
    frame_type = FrameType(data[0])
    length = (data[1] << 16) | (data[2] << 8) | data[3]
    payload, _ = opack.unpack(data[4 : 4 + length])
    payload["_pd"] = hap_tlv8.read_tlv(payload["_pd"])
    return Frame(frame_type, payload), data[4 + length :]


def encode_frame(frame_type: FrameType, data: bytes):
    """Encode a frame as bytes."""
    payload = opack.pack(data)
    header = bytes([frame_type.value]) + len(payload).to_bytes(3, byteorder="big")
    return header + payload


class CompanionPairingProcedure:
    """Perform pairing and return new credentials."""

    def __init__(self, protocol, srp):
        """Initialize a new CompanionPairingHandler."""
        self.protocol = protocol
        self.srp = srp
        self._atv_salt = None
        self._atv_pub_key = None

    # TODO: Should not be here
    async def _send_and_receive(self, frame_type, message):
        frame = encode_frame(frame_type, message)
        resp = await self.protocol.send_and_receive(frame)
        return decode_frame(resp)[0]

    async def start_pairing(self):
        """Start pairing procedure."""
        self.srp.initialize()

        msg = {
            "_pd": hap_tlv8.write_tlv(
                {hap_tlv8.TLV_METHOD: b"\x00", hap_tlv8.TLV_SEQ_NO: b"\x01"}
            ),
            "_pwTy": 1,
        }
        resp = await self._send_and_receive(FrameType.PS_Start, msg)

        pairing_data = resp.data["_pd"]
        self._atv_salt = pairing_data[hap_tlv8.TLV_SALT]
        self._atv_pub_key = pairing_data[hap_tlv8.TLV_PUBLIC_KEY]
        log_binary(
            _LOGGER,
            "Got pub key and salt",
            Salt=self._atv_salt,
            PubKey=self._atv_pub_key,
        )

    async def finish_pairing(self, pin):
        """Finish pairing process."""
        self.srp.step1(pin)

        pub_key, proof = self.srp.step2(self._atv_pub_key, self._atv_salt)

        msg = {
            "_pd": hap_tlv8.write_tlv(
                {
                    hap_tlv8.TLV_SEQ_NO: b"\x03",
                    hap_tlv8.TLV_PUBLIC_KEY: pub_key,
                    hap_tlv8.TLV_PROOF: proof,
                }
            ),
            "_pwTy": 1,
        }

        resp = await self._send_and_receive(FrameType.PS_Next, msg)

        pairing_data = resp.data["_pd"]
        atv_proof = pairing_data[hap_tlv8.TLV_PROOF]
        log_binary(_LOGGER, "Device", Proof=atv_proof)

        encrypted_data = self.srp.step3()
        msg = {
            "_pd": hap_tlv8.write_tlv(
                {
                    hap_tlv8.TLV_SEQ_NO: b"\x05",
                    hap_tlv8.TLV_ENCRYPTED_DATA: encrypted_data,
                }
            ),
            "_pwTy": 1,
        }
        resp = await self._send_and_receive(FrameType.PS_Next, msg)

        pairing_data = resp.data["_pd"]
        encrypted_data = pairing_data[hap_tlv8.TLV_ENCRYPTED_DATA]

        return self.srp.step4(encrypted_data)


class CompanionPairingVerifier:
    """Verify credentials and derive new encryption keys."""

    def __init__(self, protocol, srp, credentials):
        """Initialize a new MrpPairingVerifier."""
        self.protocol = protocol
        self.srp = srp
        self.credentials = credentials
        self._output_key = None
        self._input_key = None

    # TODO: Should not be here
    async def _send_and_receive(self, frame_type, message):
        frame = encode_frame(frame_type, message)
        resp = await self.protocol.send_and_receive(frame)
        return decode_frame(resp)[0]

    async def verify_credentials(self):
        """Verify credentials with device."""
        _, public_key = self.srp.initialize()
        print("public key:", public_key)

        msg = {
            "_pd": tlv8.write_tlv(
                {tlv8.TLV_SEQ_NO: b"\x01", tlv8.TLV_PUBLIC_KEY: public_key}
            ),
            "_auTy": 4,
        }

        resp = await self._send_and_receive(FrameType.PV_Start, msg)

        pairing_data = resp.data["_pd"]
        session_pub_key = pairing_data[tlv8.TLV_PUBLIC_KEY]
        encrypted = pairing_data[tlv8.TLV_ENCRYPTED_DATA]
        log_binary(_LOGGER, "Device", Public=self.credentials.ltpk, Encrypted=encrypted)

        encrypted_data = self.srp.verify1(self.credentials, session_pub_key, encrypted)
        msg = {
            "_pd": tlv8.write_tlv(
                {tlv8.TLV_SEQ_NO: b"\x03", tlv8.TLV_ENCRYPTED_DATA: encrypted_data}
            ),
        }
        resp = await self._send_and_receive(FrameType.PV_Next, msg)
        print("resp:", resp)

        # TODO: check status code

        self._output_key, self._input_key = self.srp.verify2()
        print("output key:", self._output_key, ", input key:", self._input_key)

    def encryption_keys(self):
        """Return derived encryption keys."""
        return self._output_key, self._input_key
