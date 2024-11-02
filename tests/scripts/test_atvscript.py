"""Smoke test for atvscript."""

import json
import logging

from deepdiff import DeepDiff
import pytest

from pyatv.const import Protocol

from tests.scripts.conftest import AIRPLAY_ID, DMAP_ID, IP_1, IP_2, MRP_ID

_LOGGER = logging.getLogger(__name__)
HASH = "ca496c14642c78af6dd4250191fe175f6dafd72b4c33bcbab43c454aae051da1"

pytestmark = pytest.mark.asyncio


def assert_json_output(output, expected):
    _LOGGER.debug("ACTUAL: %s", output)
    _LOGGER.debug("EXPECTED: %s", expected)

    actual = json.loads(output)

    # Hack for now: only check that datetime is present to work around issue with
    # different time zones.
    assert "datetime" in actual
    del actual["datetime"]

    assert not DeepDiff(actual, expected, ignore_order=True)


async def test_scan_devices(scriptenv, fake_atv):
    stdout, _, exit_code = await scriptenv("atvscript", "scan")
    assert_json_output(
        stdout,
        {
            "result": "success",
            "devices": [
                {
                    "name": "Apple TV 1",
                    "address": IP_1,
                    "identifier": DMAP_ID,
                    "all_identifiers": [DMAP_ID],
                    "device_info": {
                        "mac": None,
                        "model": "Unknown",
                        "model_str": "Unknown",
                        "operating_system": "Legacy",
                        "version": None,
                    },
                    "services": [{"protocol": "dmap", "port": 3689}],
                },
                {
                    "name": "Apple TV 2",
                    "address": IP_2,
                    "identifier": MRP_ID,
                    "all_identifiers": [AIRPLAY_ID, MRP_ID],
                    "device_info": {
                        "mac": AIRPLAY_ID,
                        "model": "Unknown",
                        "model_str": "pyatv",
                        "operating_system": "TvOS",
                        "version": "14.7",
                    },
                    "services": [
                        {
                            "protocol": "mrp",
                            "port": fake_atv.get_port(Protocol.MRP),
                        },
                        {
                            "protocol": "airplay",
                            "port": fake_atv.get_port(Protocol.AirPlay),
                        },
                    ],
                },
            ],
        },
    )
    assert exit_code == 0


async def test_mrp_idle(scriptenv):
    stdout, _, exit_code = await scriptenv("atvscript", "--id", MRP_ID, "playing")
    assert_json_output(
        stdout,
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
            "content_identifier": None,
            "itunes_store_identifier": None,
        },
    )
    assert exit_code == 0
