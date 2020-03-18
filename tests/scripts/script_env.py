"""Simulated environment for functional script testing."""

import sys
from importlib import import_module

from contextlib import contextmanager
from io import StringIO

from unittest.mock import patch

from aiohttp.test_utils import AioHTTPTestCase

import pyatv
from tests import fake_udns, zeroconf_stub
from tests.utils import stub_sleep
from tests.mrp.fake_mrp_atv import FakeAppleTV, AppleTVUseCases


IP_1 = "10.0.0.1"
IP_2 = "127.0.0.1"
DMAP_ID = "dmap_id"
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

    def setup_environment(self):
        airplay_port = self.server.port

        services = []
        services.append(
            zeroconf_stub.homesharing_service(DMAP_ID, b"Apple TV 1", IP_1, b"aaaa")
        )
        services.append(
            zeroconf_stub.mrp_service(
                "DDDD", b"Apple TV 2", IP_2, MRP_ID, port=self.fake_atv.port
            )
        )
        services.append(
            zeroconf_stub.airplay_service(
                "Apple TV 2", IP_2, AIRPLAY_ID, port=airplay_port
            )
        )
        zeroconf_stub.stub(pyatv, *services)

        self.fake_udns.add_service(
            fake_udns.mrp_service("DDDD", "Apple TV 2", MRP_ID, port=self.fake_atv.port)
        )
        self.fake_udns.add_service(
            fake_udns.airplay_service("Apple TV 2", AIRPLAY_ID, port=airplay_port)
        )

        self.usecase.airplay_playback_playing()
        self.usecase.airplay_playback_idle()

    async def get_application(self, loop=None):
        self.fake_atv = FakeAppleTV(self, self.loop)
        self.usecase = AppleTVUseCases(self.fake_atv)
        self.fake_udns = fake_udns.FakeUdns(self.loop)
        return self.fake_atv.app

    def user_input(self, text):
        self.inputs.append(text)

    def has_output(self, *strings):
        for string in strings:
            self.assertIn(string, self.stdout)

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
                module = import_module(f"pyatv.scripts.{script}")
                self.retcode = await module.appstart(self.loop)
                self.stdout = out.getvalue()
                self.stderr = err.getvalue()
