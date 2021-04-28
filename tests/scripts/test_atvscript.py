"""Smoke test for atvscript."""

import json
import logging

from aiohttp.test_utils import unittest_run_loop
from deepdiff import DeepDiff

from pyatv.const import Protocol

from tests.scripts.script_env import DMAP_ID, IP_1, IP_2, MRP_ID, ScriptTest

_LOGGER = logging.getLogger(__name__)
HASH = "ca496c14642c78af6dd4250191fe175f6dafd72b4c33bcbab43c454aae051da1"


class AtvscriptTest(ScriptTest):
    async def atvscript(self, *args):
        return await self.run_script("atvscript", *args)

    def assertJsonOutput(self, expected):
        _LOGGER.debug("ACTUAL: %s", self.stdout)
        _LOGGER.debug("EXPECTED: %s", expected)

        actual = json.loads(self.stdout)

        # Hack for now: only check that datetime is present to work around issue with
        # different time zones.
        self.assertIn("datetime", actual)
        del actual["datetime"]

        self.assertEqual(DeepDiff(actual, expected, ignore_order=True), {})

    @unittest_run_loop
    async def test_scan_devices(self):
        await self.atvscript("scan")
        self.assertJsonOutput(
            {
                "result": "success",
                "devices": [
                    {
                        "name": "Apple TV 1",
                        "address": IP_1,
                        "identifier": DMAP_ID,
                        "services": [{"protocol": "dmap", "port": 3689}],
                    },
                    {
                        "name": "Apple TV 2",
                        "address": IP_2,
                        "identifier": MRP_ID,
                        "services": [
                            {
                                "protocol": "mrp",
                                "port": self.fake_atv.get_port(Protocol.MRP),
                            },
                            {"protocol": "airplay", "port": self.server.port},
                        ],
                    },
                ],
            },
        )
        self.exit(0)

    @unittest_run_loop
    async def test_mrp_idle(self):
        await self.atvscript("--id", MRP_ID, "playing")
        self.assertJsonOutput(
            {
                "result": "success",
                "hash": HASH,
                "media_type": "unknown",
                "device_state": "idle",
                "title": None,
                "artist": None,
                "album": None,
                "genre": None,
                "total_time": None,
                "position": None,
                "shuffle": "off",
                "repeat": "off",
                "app": None,
                "app_id": None,
                "series_name": None,
                "season_number": None,
                "episode_number": None,
            }
        )
        self.exit(0)
