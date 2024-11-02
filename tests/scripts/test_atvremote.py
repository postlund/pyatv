"""Smoke test for atvremote."""

import asyncio

import pytest

from pyatv.auth.hap_pairing import parse_credentials
from pyatv.auth.server_auth import CLIENT_CREDENTIALS
from pyatv.const import Protocol

from tests.fake_device.airplay import DEVICE_AUTH_KEY, DEVICE_CREDENTIALS, DEVICE_PIN
from tests.scripts.conftest import AIRPLAY_ID, DMAP_ID, IP_1, IP_2, MRP_ID
from tests.utils import all_in

pytestmark = pytest.mark.asyncio


async def test_scan_devices(scriptenv):
    stdout, _, exit_code = await scriptenv("atvremote", "scan")
    assert all_in(
        stdout, "Apple TV 1", "Apple TV 2", IP_1, IP_2, MRP_ID, AIRPLAY_ID, DMAP_ID
    )
    assert exit_code == 0


async def test_scan_hosts(scriptenv):
    stdout, _, exit_code = await scriptenv(
        "atvremote", "--scan-hosts", "127.0.0.1", "scan"
    )
    assert all_in(stdout, "Apple TV 2", IP_2, MRP_ID, AIRPLAY_ID)
    assert exit_code == 0


async def test_scan_single_identifier(scriptenv):
    stdout, _, exit_code = await scriptenv("atvremote", "--id", MRP_ID, "scan")
    assert all_in(stdout, "Apple TV 2", IP_2, MRP_ID, AIRPLAY_ID)
    assert exit_code == 0


async def test_scan_multiple_identifier(scriptenv):
    stdout, _, exit_code = await scriptenv(
        "atvremote", "--id", f"bad_id,{DMAP_ID}", "scan"
    )
    assert all_in(
        stdout,
        "Apple TV 1",
        IP_1,
        DMAP_ID,
    )
    assert exit_code == 0


async def test_pair_airplay(scriptenv):
    stdout, _, exit_code = await scriptenv(
        "atvremote",
        "--address",
        IP_2,
        "--protocol",
        "airplay",
        "--id",
        MRP_ID,
        "pair",
        inputs=[str(DEVICE_PIN)],
    )
    assert all_in(
        stdout,
        "Enter PIN",
        "seems to have succeeded",
        str(parse_credentials(DEVICE_CREDENTIALS)),
    )
    assert exit_code == 0


async def test_airplay_play_url(scriptenv):
    _, _, exit_code = await scriptenv(
        "atvremote",
        "--id",
        MRP_ID,
        "--airplay-credentials",
        DEVICE_CREDENTIALS,
        "play_url=http://fake",
        inputs=[str(DEVICE_PIN)],
    )
    assert exit_code == 0


async def test_mrp_idle(scriptenv):
    stdout, _, exit_code = await scriptenv("atvremote", "--id", MRP_ID, "playing")
    assert all_in(stdout, "Media type: Unknown", "Device state: Idle")
    assert exit_code == 0


async def test_device_info(scriptenv):
    stdout, _, exit_code = await scriptenv("atvremote", "--id", MRP_ID, "device_info")
    assert all_in(stdout, "tvOS", AIRPLAY_ID)
    assert exit_code == 0


async def test_mrp_auth(scriptenv, fake_atv):
    stdout, _, exit_code = await scriptenv(
        "atvremote", "--id", MRP_ID, "--mrp-credentials", CLIENT_CREDENTIALS, "playing"
    )
    assert fake_atv.get_state(Protocol.MRP).has_authenticated
    assert all_in(stdout, "Device state: Idle")
    assert exit_code == 0


async def test_mrp_auth_error(scriptenv, fake_atv):
    _, stderr, exit_code = await scriptenv(
        "atvremote", "--id", MRP_ID, "--mrp-credentials", "30:31:32:33", "playing"
    )
    assert not fake_atv.get_state(Protocol.MRP).has_authenticated
    assert all_in(stderr, "AuthenticationError")
    assert exit_code == 1


async def test_manual_connect(scriptenv, fake_atv):
    stdout, _, exit_code = await scriptenv(
        "atvremote",
        "--address",
        IP_2,
        "--protocol",
        "mrp",
        "--port",
        str(fake_atv.get_port(Protocol.MRP)),
        "--id",
        MRP_ID,
        "--manual",
        "playing",
        inputs=[str(DEVICE_PIN)],
    )
    assert all_in(stdout, "Media type: Unknown", "Device state: Idle")
    assert exit_code == 0


async def test_settings(scriptenv):
    # Check setting has default value (None)
    stdout, _, exit_code = await scriptenv(
        "atvremote", "--id", MRP_ID, "print_settings", persistent_storage=True
    )
    assert all_in(stdout, "protocols.raop.password = None")
    assert exit_code == 0

    # Change value of protocols.raop.password
    _, _, exit_code = await scriptenv(
        "atvremote",
        "--id",
        MRP_ID,
        "change_setting=protocols.raop.password,foo",
        persistent_storage=True,
    )
    assert exit_code == 0

    # Check value was updated
    stdout, _, exit_code = await scriptenv(
        "atvremote", "--id", MRP_ID, "print_settings", persistent_storage=True
    )

    assert all_in(stdout, "protocols.raop.password = foo")
    assert exit_code == 0

    # Unset value of protocols.raop.password (to None)
    stdout, _, exit_code = await scriptenv(
        "atvremote",
        "--id",
        MRP_ID,
        "unset_setting=protocols.raop.password",
        persistent_storage=True,
    )
    assert exit_code == 0

    # Check value was updated
    stdout, _, exit_code = await scriptenv(
        "atvremote", "--id", MRP_ID, "print_settings", persistent_storage=True
    )
    assert all_in(stdout, "protocols.raop.password = None")
    assert exit_code == 0


async def test_wizard(scriptenv):
    # Run the wizard but limit scanning to a single device since scanning order might
    # become unpredictable otherwise
    stdout, _, exit_code = await scriptenv(
        "atvremote",
        "-s",
        IP_2,
        "wizard",
        inputs=["1", str(DEVICE_PIN)],
        persistent_storage=True,
    )
    assert all_in(stdout, "MRP is disabled", "Pairing finished", "Currently playing")
    assert exit_code == 0

    # Check that credentials was saved to storage
    stdout, _, exit_code = await scriptenv(
        "atvremote", "-s", IP_2, "print_settings", persistent_storage=True
    )
    assert all_in(stdout, DEVICE_AUTH_KEY.lower())
    assert exit_code == 0
