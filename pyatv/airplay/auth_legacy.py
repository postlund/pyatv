"""Implementation of legacy pairing for AirPlay."""

import binascii
import logging
import plistlib
from typing import Dict, Tuple

from pyatv import exceptions
from pyatv.airplay.srp import SRPAuthHandler
from pyatv.auth.hap_pairing import (
    HapCredentials,
    PairSetupProcedure,
    PairVerifyProcedure,
)
from pyatv.exceptions import AuthenticationError
from pyatv.support.http import HttpConnection, HttpResponse

_LOGGER = logging.getLogger(__name__)

_AIRPLAY_HEADERS = {
    "User-Agent": "AirPlay/320.20",
    "Connection": "keep-alive",
}


class AirPlayLegacyPairSetupProcedure(PairSetupProcedure):
    """Authenticate a device for AirPlay playback."""

    def __init__(self, http: HttpConnection, auth_handler: SRPAuthHandler) -> None:
        """Initialize a new AirPlayLegacyPairSetupProcedure."""
        self.http = http
        self.srp = auth_handler

    async def start_pairing(self) -> None:
        """Start the pairing process.

        This method will show the expected PIN on screen.
        """
        resp = await self.http.post("/pair-pin-start", headers=_AIRPLAY_HEADERS)
        if resp.code != 200:
            raise AuthenticationError("pair start failed")

    async def finish_pairing(self, username: str, pin_code: int) -> HapCredentials:
        """Finish pairing process.

        A username (generated by new_credentials) and the PIN code shown on
        screen must be provided.
        """
        # Step 1
        self.srp.step1(username, pin_code)
        resp = await self._send_plist(method="pin", user=username)
        resp = plistlib.loads(
            resp.body if isinstance(resp.body, bytes) else resp.body.encode("utf-8")
        )
        if not isinstance(resp, dict):
            raise exceptions.ProtocolError(f"exoected dict, got {type(resp)}")

        # Step 2
        pub_key, key_proof = self.srp.step2(resp["pk"], resp["salt"])
        await self._send_plist(
            pk=binascii.unhexlify(pub_key), proof=binascii.unhexlify(key_proof)
        )

        # Step 3
        epk, tag = self.srp.step3()
        await self._send_plist(epk=epk, authTag=tag)
        return self.srp.credentials

    async def _send_plist(self, **kwargs) -> HttpResponse:
        plist: Dict[str, str] = dict((str(k), v) for k, v in kwargs.items())

        headers = _AIRPLAY_HEADERS.copy()
        headers["Content-Type"] = "application/x-apple-binary-plist"

        # TODO: For some reason pylint does not find FMT_BINARY, why?
        # pylint: disable=no-member
        return await self.http.post(
            "/pair-setup-pin", body=plistlib.dumps(plist, fmt=plistlib.FMT_BINARY)
        )


class AirPlayLegacyPairVerifyProcedure(PairVerifyProcedure):
    """Verify if a device is allowed to perform AirPlay playback."""

    def __init__(self, http: HttpConnection, auth_handler: SRPAuthHandler) -> None:
        """Initialize a new AirPlayPairingVerifier."""
        self.http = http
        self.srp = auth_handler

    async def verify_credentials(self) -> bool:
        """Verify if device is allowed to use AirPlau."""
        resp = await self._send(self.srp.verify1())

        atv_public_secret = resp.body[0:32]
        data = resp.body[32:]  # TODO: what is this?
        await self._send(self.srp.verify2(atv_public_secret, data))
        return True

    async def _send(self, data: bytes) -> HttpResponse:
        headers = _AIRPLAY_HEADERS.copy()
        headers["Content-Type"] = "application/octet-stream"
        return await self.http.post("/pair-verify", headers=headers, body=data)

    @staticmethod
    def encryption_keys() -> Tuple[str, str]:
        """Return derived encryption keys."""
        raise exceptions.NotSupportedError(
            "encryption keys not supported by legacy auth"
        )
