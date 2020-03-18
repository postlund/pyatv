"""Smoke test for atvscript."""

import json

from deepdiff import DeepDiff
from aiohttp.test_utils import unittest_run_loop

from tests.scripts.script_env import IP_1, IP_2, DMAP_ID, MRP_ID, ScriptTest

HASH = "ca496c14642c78af6dd4250191fe175f6dafd72b4c33bcbab43c454aae051da1"


class AtvscriptTest(ScriptTest):
    async def atvscript(self, *args):
        return await self.run_script("atvscript", *args)

    def assertJsonOutput(self, expected):
        actual = json.loads(self.stdout)
        print(actual)
        self.assertEqual(DeepDiff(actual, expected), {})

    @unittest_run_loop
    async def test_scan_devices(self):
        await self.atvscript("scan")
        self.assertJsonOutput(
            {
                "result": "success",
                "devices": [
                    {"name": "Apple TV 1", "address": IP_1, "identifier": DMAP_ID},
                    {"name": "Apple TV 2", "address": IP_2, "identifier": MRP_ID},
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
            }
        )
        self.exit(0)
