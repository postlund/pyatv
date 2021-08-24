"""Unit tests for pyatv.airplay.auth."""

from unittest.mock import MagicMock, patch

import pytest

from pyatv.airplay.auth import (
    HapCredentials,
    NullPairVerifyProcedure,
    pair_setup,
    pair_verify,
)
from pyatv.airplay.auth.legacy import (
    AirPlayLegacyPairSetupProcedure,
    AirPlayLegacyPairVerifyProcedure,
)
from pyatv.auth.hap_pairing import NO_CREDENTIALS, HapCredentials

# Legacy credentials only have ltsk (seed) and client_id (identifier) filled in
LEGACY_CREDENTIALS = HapCredentials(b"", b"1", b"", b"2")
NEW_LEGACY_CREDENTIALS = HapCredentials(b"", b"3", b"", b"4")


@pytest.fixture(name="srp")
def srp_fixture():
    with patch("pyatv.airplay.auth.SRPAuthHandler") as srp:
        yield srp


@pytest.fixture(name="connection")
def connection_fixture():
    yield MagicMock()


def test_pair_setup_legacy_with_existing_credentials(srp, connection):
    procedure = pair_setup(LEGACY_CREDENTIALS, connection)

    srp.assert_called_with(LEGACY_CREDENTIALS)
    assert isinstance(procedure, AirPlayLegacyPairSetupProcedure)


@patch("pyatv.airplay.auth.new_credentials", return_value=NEW_LEGACY_CREDENTIALS)
def test_pair_setup_legacy_with_new_credentials(new_credentials, srp, connection):
    procedure = pair_setup(NO_CREDENTIALS, connection)

    srp.assert_called_with(NEW_LEGACY_CREDENTIALS)
    assert isinstance(procedure, AirPlayLegacyPairSetupProcedure)


def test_pair_verify_legacy(srp, connection):
    procedure = pair_verify(LEGACY_CREDENTIALS, connection)

    srp.assert_called_with(LEGACY_CREDENTIALS)
    assert isinstance(procedure, AirPlayLegacyPairVerifyProcedure)


def test_pair_verify_legacy_no_credentials(srp, connection):
    procedure = pair_verify(NO_CREDENTIALS, connection)

    srp.assert_not_called()
    assert isinstance(procedure, NullPairVerifyProcedure)
