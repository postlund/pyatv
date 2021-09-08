"""Unit tests for pyatv.protocols.airplay.auth."""

from unittest.mock import MagicMock, patch

import pytest

from pyatv.auth.hap_pairing import NO_CREDENTIALS, HapCredentials
from pyatv.protocols.airplay.auth import (
    AuthenticationType,
    HapCredentials,
    NullPairVerifyProcedure,
    pair_setup,
    pair_verify,
)
from pyatv.protocols.airplay.auth.hap import (
    AirPlayHapPairSetupProcedure,
    AirPlayHapPairVerifyProcedure,
)
from pyatv.protocols.airplay.auth.legacy import (
    AirPlayLegacyPairSetupProcedure,
    AirPlayLegacyPairVerifyProcedure,
)

# Legacy credentials only have ltsk (seed) and client_id (identifier) filled in
LEGACY_CREDENTIALS = HapCredentials(b"", b"1", b"", b"2")

HAP_CREDENTIALS = HapCredentials(b"1", b"2", b"3", b"4")


@pytest.fixture(name="srp")
def srp_fixture():
    with patch("pyatv.protocols.airplay.auth.LegacySRPAuthHandler") as srp:
        yield srp


@pytest.fixture(name="connection")
def connection_fixture():
    yield MagicMock()


# No authentication


def test_pair_verify_no_credentials(srp, connection):
    procedure = pair_verify(NO_CREDENTIALS, connection)

    srp.assert_not_called()
    assert isinstance(procedure, NullPairVerifyProcedure)


# Legacy authentication


@patch("pyatv.protocols.airplay.auth.new_credentials", return_value=LEGACY_CREDENTIALS)
def test_pair_setup_legacy(new_credentials, srp, connection):
    procedure = pair_setup(AuthenticationType.Legacy, connection)

    srp.assert_called_with(LEGACY_CREDENTIALS)
    assert isinstance(procedure, AirPlayLegacyPairSetupProcedure)


def test_pair_verify_legacy(srp, connection):
    procedure = pair_verify(LEGACY_CREDENTIALS, connection)

    srp.assert_called_with(LEGACY_CREDENTIALS)
    assert isinstance(procedure, AirPlayLegacyPairVerifyProcedure)


# HAP authentication


def test_pair_setup_hap(connection):
    procedure = pair_setup(AuthenticationType.HAP, connection)
    assert isinstance(procedure, AirPlayHapPairSetupProcedure)


def test_pair_verify_hap(connection):
    procedure = pair_verify(HAP_CREDENTIALS, connection)
    assert isinstance(procedure, AirPlayHapPairVerifyProcedure)
