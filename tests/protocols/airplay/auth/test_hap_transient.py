"""Unit tests for pyatv.protocols.airplay.auth.hap_transient."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from pyatv.auth import hap_tlv8
from pyatv.auth.hap_srp import SRPAuthHandler
from pyatv.exceptions import AuthenticationError
from pyatv.protocols.airplay.auth.hap_transient import (
    AirPlayHapTransientPairVerifyProcedure,
    check_pairing_error,
)
from pyatv.support.http import HttpResponse


def _response(data):
    return HttpResponse("HTTP", "1.1", 200, "OK", {}, hap_tlv8.write_tlv(data))


def test_check_pairing_error_no_error():
    check_pairing_error({hap_tlv8.TlvValue.SeqNo: b"\x04"}, "M4")


def test_check_pairing_error_authentication_with_backoff():
    with pytest.raises(AuthenticationError, match="M4.*error 2.*retry after 256s"):
        check_pairing_error(
            {
                hap_tlv8.TlvValue.Error: b"\x02",
                hap_tlv8.TlvValue.BackOff: b"\x00\x01",
            },
            "M4",
        )


@pytest.mark.asyncio
async def test_transient_verify_raises_on_m4_error():
    """Device rejects the proof: must not enable crypto."""
    srp = SRPAuthHandler()
    m2 = {
        hap_tlv8.TlvValue.SeqNo: b"\x02",
        hap_tlv8.TlvValue.Salt: b"\x01" * 16,
        hap_tlv8.TlvValue.PublicKey: b"\x02" * 384,
    }
    m4 = {
        hap_tlv8.TlvValue.Error: b"\x02",
        hap_tlv8.TlvValue.SeqNo: b"\x04",
        hap_tlv8.TlvValue.BackOff: b"\x80",
    }
    http = MagicMock()
    http.post = AsyncMock(
        side_effect=[
            HttpResponse("HTTP", "1.1", 200, "OK", {}, b""),
            _response(m2),
            _response(m4),
        ]
    )

    verifier = AirPlayHapTransientPairVerifyProcedure(http, srp)
    with pytest.raises(AuthenticationError, match="error 2"):
        await verifier.verify_credentials()


@pytest.mark.asyncio
async def test_transient_verify_raises_on_m2_backoff():
    srp = SRPAuthHandler()
    m2 = {
        hap_tlv8.TlvValue.Error: b"\x03",
        hap_tlv8.TlvValue.SeqNo: b"\x02",
        hap_tlv8.TlvValue.BackOff: b"\x3c",
    }
    http = MagicMock()
    http.post = AsyncMock(
        side_effect=[HttpResponse("HTTP", "1.1", 200, "OK", {}, b""), _response(m2)]
    )

    verifier = AirPlayHapTransientPairVerifyProcedure(http, srp)
    with pytest.raises(AuthenticationError, match="M2.*retry after 60s"):
        await verifier.verify_credentials()
