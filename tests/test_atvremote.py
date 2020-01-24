"""Smoke test for atvremote."""

import sys

from contextlib import contextmanager
from io import StringIO

from unittest.mock import patch

from aiohttp.test_utils import (AioHTTPTestCase, unittest_run_loop)

import pyatv
from pyatv import __main__ as atvremote
from tests import fake_udns, zeroconf_stub
from tests.utils import stub_sleep
from tests.airplay.fake_airplay_device import DEVICE_PIN, DEVICE_CREDENTIALS
from tests.mrp.fake_mrp_atv import (
    FakeAppleTV, AppleTVUseCases)
from tests.mrp.mrp_server_auth import CLIENT_CREDENTIALS


IP_1 = '10.0.0.1'
IP_2 = '127.0.0.1'
DMAP_ID = 'dmap_id'
MRP_ID = 'mrp_id'
AIRPLAY_ID = 'AA:BB:CC:DD:EE:FF'


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


class AtvremoteTest(AioHTTPTestCase):

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
        services.append(zeroconf_stub.homesharing_service(
                DMAP_ID, b'Apple TV 1', IP_1, b'aaaa'))
        services.append(zeroconf_stub.mrp_service(
                'DDDD', b'Apple TV 2', IP_2, MRP_ID, port=self.fake_atv.port))
        services.append(zeroconf_stub.airplay_service(
                'Apple TV 2', IP_2, AIRPLAY_ID, port=airplay_port))
        zeroconf_stub.stub(pyatv, *services)

        self.fake_udns.add_service(fake_udns.mrp_service(
                'DDDD', 'Apple TV 2', MRP_ID, port=self.fake_atv.port))
        self.fake_udns.add_service(fake_udns.airplay_service(
                'Apple TV 2', AIRPLAY_ID, port=airplay_port))

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

    async def atvremote(self, *args):
        argv = ['atvremote'] + list(args)
        inputs = '\n'.join(self.inputs) + '\n'
        with capture_output(argv, inputs) as (out, err):
            udns_port = str(self.fake_udns.port)
            with patch.dict('os.environ', {'PYATV_UDNS_PORT': udns_port}):
                self.retcode = await atvremote.appstart(self.loop)
                self.stdout = out.getvalue()
                self.stderr = err.getvalue()

    @unittest_run_loop
    async def test_scan_devices(self):
        await self.atvremote("scan")
        self.has_output("Apple TV 1",
                        "Apple TV 2",
                        IP_1,
                        IP_2,
                        MRP_ID,
                        AIRPLAY_ID,
                        DMAP_ID)
        self.exit(0)

    @unittest_run_loop
    async def test_scan_hosts(self):
        await self.atvremote(
            "--scan-hosts",
            "127.0.0.1",
            "scan")
        self.has_output("Apple TV 2",
                        IP_2,
                        MRP_ID,
                        AIRPLAY_ID)
        self.exit(0)

    @unittest_run_loop
    async def test_pair_airplay(self):
        self.user_input(str(DEVICE_PIN))
        await self.atvremote(
            "--address", IP_2,
            "--protocol", "airplay",
            "--id", MRP_ID,
            "--airplay-credentials", DEVICE_CREDENTIALS,
            "pair")
        self.has_output("Enter PIN",
                        "seems to have succeeded",
                        DEVICE_CREDENTIALS)
        self.exit(0)

    @unittest_run_loop
    async def test_airplay_play_url(self):
        self.user_input(str(DEVICE_PIN))
        await self.atvremote(
            "--id", MRP_ID,
            "--airplay-credentials", DEVICE_CREDENTIALS,
            "play_url=http://fake")
        self.exit(0)

    @unittest_run_loop
    async def test_mrp_idle(self):
        await self.atvremote("--id", MRP_ID, "playing")
        self.has_output("Media type: Unknown", "Device state: Idle")
        self.exit(0)

    @unittest_run_loop
    async def test_mrp_auth(self):
        await self.atvremote(
            "--id", MRP_ID,
            "--mrp-credentials", CLIENT_CREDENTIALS,
            "playing")
        self.assertTrue(self.fake_atv.has_authenticated)
        self.has_output("Device state: Idle")
        self.exit(0)

    @unittest_run_loop
    async def test_mrp_auth_error(self):
        await self.atvremote(
            "--id", MRP_ID,
            "--mrp-credentials", "30:31:32:33",
            "playing")
        self.assertFalse(self.fake_atv.has_authenticated)
        self.has_error("AuthenticationError:")
        self.exit(1)

    @unittest_run_loop
    async def test_manual_connect(self):
        self.user_input(str(DEVICE_PIN))
        await self.atvremote(
            "--address", IP_2,
            "--protocol", "mrp",
            "--port", str(self.fake_atv.port),
            "--id", MRP_ID,
            "--manual",
            "playing")
        self.has_output("Media type: Unknown", "Device state: Idle")
        self.exit(0)
