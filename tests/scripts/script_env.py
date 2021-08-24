"""Simulated environment for functional script testing."""

from contextlib import contextmanager
from importlib import import_module
from io import StringIO
import sys
from unittest.mock import patch

from aiohttp.test_utils import AioHTTPTestCase

import pyatv
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


class ScriptTest(AioHTTPTestCase):
    async def setUpAsync(self):
        await AioHTTPTestCase.setUpAsync(self)
        stub_sleep()
        self.setup_environment()
        await self.fake_udns.start()
        self.stdout = None
        self.stderr = None
        self.retcode = None
        self.inputs = []

    def tearDown(self):
        unstub_sleep()
        AioHTTPTestCase.tearDown(self)

    def setup_environment(self):
        airplay_port = self.server.port

        self.fake_udns.add_service(
            fake_udns.homesharing_service(
                DMAP_ID, "Apple TV 1", "aaaa", addresses=[IP_1]
            )
        )

        self.fake_udns.add_service(
            fake_udns.mrp_service(
                "DDDD",
                "Apple TV 2",
                MRP_ID,
                addresses=[IP_2],
                port=self.fake_atv.get_port(Protocol.MRP),
            )
        )
        self.fake_udns.add_service(
            fake_udns.airplay_service(
                "Apple TV 2", AIRPLAY_ID, addresses=[IP_2], port=airplay_port
            )
        )

        self.airplay_usecase.airplay_playback_playing()
        self.airplay_usecase.airplay_playback_idle()

    async def get_application(self, loop=None):
        self.fake_udns = fake_udns.FakeUdns(self.loop)
        self.fake_udns.ip_filter = IP_2
        self.fake_atv = FakeAppleTV(self.loop)
        self.state, self.usecase = self.fake_atv.add_service(Protocol.MRP)
        self.airplay_state, self.airplay_usecase = self.fake_atv.add_service(
            Protocol.AirPlay
        )
        return self.fake_atv.app

    def user_input(self, text):
        self.inputs.append(text)

    def has_output(self, *objs):
        for obj in objs:
            self.assertIn(str(obj), self.stdout)

    def has_error(self, *strings):
        for string in strings:
            self.assertIn(string, self.stderr)

    def exit(self, code):
        self.assertEqual(self.retcode, code)

    async def run_script(self, script, *args):
        argv = [script] + list(args)
        inputs = "\n".join(self.inputs) + "\n"
        with capture_output(argv, inputs) as (out, err):
            udns_port = str(self.fake_udns.port)
            with patch.dict("os.environ", {"PYATV_UDNS_PORT": udns_port}):
                with fake_udns.stub_multicast(self.fake_udns, self.loop):
                    with faketime("pyatv", 0):
                        # Stub away port knocking and ignore result (not tested here)
                        with patch("pyatv.support.knock.knock") as mock_knock:

                            async def _no_action(*args):
                                pass

                            mock_knock.side_effect = _no_action

                            module = import_module(f"pyatv.scripts.{script}")
                            self.retcode = await module.appstart(self.loop)
                            self.stdout = out.getvalue()
                            self.stderr = err.getvalue()
