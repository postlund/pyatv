"""Support for HAP transient pairing.

Technically, transient pairing only covers the first four states of regular pairing
(M1-M4). The shared secret is then used to derive keys. The way pyatv is structured
makes it easier to implement as the verification procedure step instead, so that's
how it works and why there's no setup procedure at all.
"""

import binascii
from copy import copy
import logging
from typing import Any, Dict, Tuple

from pyatv.auth import hap_tlv8
from pyatv.auth.hap_pairing import PairVerifyProcedure
from pyatv.auth.hap_srp import SRPAuthHandler, hkdf_expand
from pyatv.exceptions import InvalidResponseError
from pyatv.support import log_binary
from pyatv.support.http import HttpConnection, HttpResponse

_LOGGER = logging.getLogger(__name__)

_AIRPLAY_HEADERS = {
    "User-Agent": "AirPlay/320.20",
    "Connection": "keep-alive",
    "X-Apple-HKP": 4,
    "Content-Type": "application/octet-stream",
}

TRANSIENT_PIN = 3939


class AirPlayHapTransientPairVerifyProcedure(PairVerifyProcedure):
    """Verify if a device is allowed to perform AirPlay playback."""

    def __init__(
        self,
        http: HttpConnection,
        auth_handler: SRPAuthHandler,
    ):
        """Initialize a new AuthenticationVerifier."""
        self.http = http
        self.srp = auth_handler

    async def verify_credentials(self) -> bool:
        """Verify if device is allowed to use AirPlau."""
        self.srp.initialize()

        await self.http.post("/pair-pin-start", headers=_AIRPLAY_HEADERS)

        data = {
            hap_tlv8.TlvValue.Method: b"\x00",
            hap_tlv8.TlvValue.SeqNo: b"\x01",
            hap_tlv8.TlvValue.Flags: int.to_bytes(
                hap_tlv8.Flags.TransientPairing.value, 1, byteorder="big"
            ),
        }
        resp = await self.http.post(
            "/pair-setup", body=hap_tlv8.write_tlv(data), headers=_AIRPLAY_HEADERS
        )

        if not isinstance(resp.body, bytes):
            raise InvalidResponseError(f"got unexpected response: {resp.body}")

        pairing_data = hap_tlv8.read_tlv(resp.body)

        atv_salt = pairing_data[hap_tlv8.TlvValue.Salt]
        atv_pub_key = pairing_data[hap_tlv8.TlvValue.PublicKey]

        self.srp.step1(TRANSIENT_PIN)

        pub_key, proof = self.srp.step2(atv_pub_key, atv_salt)
        data = {
            hap_tlv8.TlvValue.SeqNo: b"\x03",
            hap_tlv8.TlvValue.PublicKey: pub_key,
            hap_tlv8.TlvValue.Proof: proof,
        }
        await self.http.post(
            "/pair-setup", body=hap_tlv8.write_tlv(data), headers=_AIRPLAY_HEADERS
        )

        return True

    async def _send(self, data: Dict[Any, Any]) -> HttpResponse:
        headers = copy(_AIRPLAY_HEADERS)
        headers["Content-Type"] = "application/octet-stream"
        return await self.http.post(
            "/pair-verify", body=hap_tlv8.write_tlv(data), headers=headers
        )

    def encryption_keys(
        self, salt: str, output_info: str, input_info: str
    ) -> Tuple[bytes, bytes]:
        """Return derived encryption keys."""
        shared = binascii.unhexlify(self.srp.shared_key)
        output_key = hkdf_expand(salt, output_info, shared)
        input_key = hkdf_expand(salt, input_info, shared)
        log_binary(_LOGGER, "Keys", Output=output_key, Input=input_key)
        return output_key, input_key
