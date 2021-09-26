"""Smoke test for atvremote."""

from aiohttp.test_utils import unittest_run_loop

from pyatv.auth.hap_pairing import parse_credentials
from pyatv.const import Protocol
from pyatv.protocols.mrp.server_auth import CLIENT_CREDENTIALS

from tests.fake_device.airplay import DEVICE_CREDENTIALS, DEVICE_PIN
from tests.scripts.script_env import AIRPLAY_ID, DMAP_ID, IP_1, IP_2, MRP_ID, ScriptTest


class AtvremoteTest(ScriptTest):
    async def atvremote(self, *args):
        return await self.run_script("atvremote", *args)

    @unittest_run_loop
    async def test_scan_devices(self):
        await self.atvremote("scan")
        self.has_output(
            "Apple TV 1", "Apple TV 2", IP_1, IP_2, MRP_ID, AIRPLAY_ID, DMAP_ID
        )
        self.exit(0)

    @unittest_run_loop
    async def test_scan_hosts(self):
        await self.atvremote("--scan-hosts", "127.0.0.1", "scan")
        self.has_output("Apple TV 2", IP_2, MRP_ID, AIRPLAY_ID)
        self.exit(0)

    @unittest_run_loop
    async def test_scan_single_identifier(self):
        await self.atvremote("--id", MRP_ID, "scan")
        self.has_output("Apple TV 2", IP_2, MRP_ID, AIRPLAY_ID)
        self.exit(0)

    @unittest_run_loop
    async def test_scan_multiple_identifier(self):
        await self.atvremote("--id", f"bad_id,{DMAP_ID}", "scan")
        self.has_output(
            "Apple TV 1",
            IP_1,
            DMAP_ID,
        )
        self.exit(0)

    @unittest_run_loop
    async def test_pair_airplay(self):
        self.user_input(str(DEVICE_PIN))
        await self.atvremote(
            "--address",
            IP_2,
            "--protocol",
            "airplay",
            "--id",
            MRP_ID,
            "pair",
        )
        self.has_output(
            "Enter PIN",
            "seems to have succeeded",
            parse_credentials(DEVICE_CREDENTIALS),
        )
        self.exit(0)

    @unittest_run_loop
    async def test_airplay_play_url(self):
        self.user_input(str(DEVICE_PIN))
        await self.atvremote(
            "--id",
            MRP_ID,
            "--airplay-credentials",
            DEVICE_CREDENTIALS,
            "play_url=http://fake",
        )
        self.exit(0)

    @unittest_run_loop
    async def test_mrp_idle(self):
        await self.atvremote("--id", MRP_ID, "playing")
        self.has_output("Media type: Unknown", "Device state: Idle")
        self.exit(0)

    @unittest_run_loop
    async def test_device_info(self):
        await self.atvremote("--id", MRP_ID, "device_info")
        self.has_output("tvOS", AIRPLAY_ID)
        self.exit(0)

    @unittest_run_loop
    async def test_mrp_auth(self):
        await self.atvremote(
            "--id", MRP_ID, "--mrp-credentials", CLIENT_CREDENTIALS, "playing"
        )
        self.assertTrue(self.state.has_authenticated)
        self.has_output("Device state: Idle")
        self.exit(0)

    @unittest_run_loop
    async def test_mrp_auth_error(self):
        await self.atvremote(
            "--id", MRP_ID, "--mrp-credentials", "30:31:32:33", "playing"
        )
        self.assertFalse(self.state.has_authenticated)
        self.has_error("AuthenticationError:")
        self.exit(1)

    @unittest_run_loop
    async def test_manual_connect(self):
        self.user_input(str(DEVICE_PIN))
        await self.atvremote(
            "--address",
            IP_2,
            "--protocol",
            "mrp",
            "--port",
            str(self.fake_atv.get_port(Protocol.MRP)),
            "--id",
            MRP_ID,
            "--manual",
            "playing",
        )
        self.has_output("Media type: Unknown", "Device state: Idle")
        self.exit(0)
