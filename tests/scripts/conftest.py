"""Simulated environment for functional script testing."""

import asyncio
from contextlib import contextmanager
from importlib import import_module
from io import StringIO
import sys
from typing import Sequence
from unittest.mock import patch

import pytest
import pytest_asyncio

from pyatv.const import Protocol

from tests import fake_udns
from tests.fake_device import FakeAppleTV
from tests.utils import faketime, stub_sleep, unstub_sleep

IP_1 = "10.0.0.1"
IP_2 = "127.0.0.1"
DMAP_ID = "dmapid"
MRP_ID = "mrp_id"
AIRPLAY_ID = "AA:BB:CC:DD:EE:FF"


@contextmanager
def capture_output(argv, inputs):
    new_out, new_err, new_in = StringIO(), StringIO(), StringIO(inputs)
    old_out, old_err, old_in = sys.stdout, sys.stderr, sys.stdin
    old_argv = sys.argv
    try:
        sys.stdout, sys.stderr, sys.stdin = new_out, new_err, new_in
        sys.argv = argv
        yield sys.stdout, sys.stderr
    finally:
        sys.stdout, sys.stderr, sys.stdin = old_out, old_err, old_in
        sys.argv = old_argv


@pytest_asyncio.fixture(name="udns")
async def udns_fixture(fake_atv):
    udns = fake_udns.FakeUdns(asyncio.get_running_loop())
    udns.ip_filter = IP_2
    await udns.start()

    udns.add_service(
        fake_udns.homesharing_service(DMAP_ID, "Apple TV 1", "aaaa", addresses=[IP_1])
    )

    udns.add_service(
        fake_udns.mrp_service(
            "DDDD",
            "Apple TV 2",
            MRP_ID,
            addresses=[IP_2],
            port=fake_atv.get_port(Protocol.MRP),
        )
    )
    udns.add_service(
        fake_udns.airplay_service(
            "Apple TV 2",
            AIRPLAY_ID,
            addresses=[IP_2],
            port=fake_atv.get_port(Protocol.AirPlay),
            model="pyatv",
        )
    )

    fake_atv.get_usecase(Protocol.AirPlay).airplay_playback_playing()
    fake_atv.get_usecase(Protocol.AirPlay).airplay_playback_idle()

    yield udns


@pytest_asyncio.fixture(name="fake_atv")
async def fake_atv_fixture():
    fake_atv = FakeAppleTV(asyncio.get_running_loop())
    fake_atv.add_service(Protocol.MRP)
    fake_atv.add_service(Protocol.AirPlay)
    await fake_atv.start()
    yield fake_atv


@pytest.fixture
def scriptenv(fake_atv, udns, mockfs):
    async def _run_script(
        script, *args, inputs: Sequence[str] = None, persistent_storage: bool = False
    ):
        loop = asyncio.get_running_loop()

        argv = [script]
        if persistent_storage:
            argv += ["--storage", "file", "--storage-file", "/pyatv.conf"]
        else:
            argv = [script, "--storage", "none"]
        argv += list(args)
        inputs = "\n".join(inputs or []) + "\n"

        with capture_output(argv, inputs) as (out, err):
            udns_port = str(udns.port)
            with patch.dict("os.environ", {"PYATV_UDNS_PORT": udns_port}):
                with fake_udns.stub_multicast(udns, loop):
                    with faketime("pyatv", 0):
                        # Stub away port knocking and ignore result (not tested here)
                        with patch("pyatv.support.knock.knock") as mock_knock:

                            async def _no_action(*args):
                                pass

                            mock_knock.side_effect = _no_action

                            module = import_module(f"pyatv.scripts.{script}")
                            exit_code = await module.appstart(loop)
                            stdout = out.getvalue()
                            stderr = err.getvalue()
                            return stdout, stderr, exit_code

    stub_sleep()
    yield _run_script
    unstub_sleep()
