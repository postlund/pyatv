"""Smoke test for atvremote."""

import sys
import asyncio

from contextlib import contextmanager
from io import StringIO

from aiohttp.test_utils import (AioHTTPTestCase, unittest_run_loop)

import pyatv
from pyatv import __main__ as atvremote
from tests import zeroconf_stub
from tests.airplay.fake_airplay_device import DEVICE_PIN, DEVICE_CREDENTIALS
from tests.mrp.fake_mrp_atv import (
    FakeAppleTV, AppleTVUseCases)


IP_1 = '10.0.0.1'
IP_2 = '127.0.0.1'
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

    def setUp(self):
        AioHTTPTestCase.setUp(self)
        self.stub_services()
        self.stdout = None
        self.stderr = None
        self.retcode = None
        self.inputs = []

        # This is a special "hack" to schedule the sleep at the end of the
        # event queue in order to give the zeroconf handlers a possibility to
        # run
        async def fake_sleep(time=None, loop=None):
            async def dummy():
                pass
            await asyncio.ensure_future(dummy())
        asyncio.sleep = fake_sleep

    def stub_services(self):
        port = self.server.port
        services = []
        services.append(zeroconf_stub.homesharing_service(
                'AAAA', b'Apple TV 1', IP_1, b'aaaa'))
        services.append(zeroconf_stub.mrp_service(
                'DDDD', b'Apple TV 2', IP_2, MRP_ID, port=port))
        services.append(zeroconf_stub.airplay_service(
                'Apple TV 2', IP_2, AIRPLAY_ID, port=port))
        zeroconf_stub.stub(pyatv, *services)

    async def get_application(self, loop=None):
        self.fake_atv = FakeAppleTV(self)
        self.usecase = AppleTVUseCases(self.fake_atv)
        await self.fake_atv.start(self.loop)
        return self.fake_atv.app

    def user_input(self, text):
        self.inputs.append(text)

    def has_output(self, *strings):
        for string in strings:
            self.assertIn(string, self.stdout)

    def exit_ok(self):
        self.assertEqual(self.retcode, 0)

    async def atvremote(self, *args):
        argv = ['atvremote'] + list(args)
        inputs = '\n'.join(self.inputs) + '\n'
        with capture_output(argv, inputs) as (out, err):
            self.retcode = await atvremote.appstart(self.loop)
            self.stdout = out.getvalue()
            self.stderr = err.getvalue()

    @unittest_run_loop
    async def test_scan_devices(self):
        await self.atvremote("scan")
        self.has_output(
            "Apple TV 1", "Apple TV 2", MRP_ID, IP_1, IP_2, AIRPLAY_ID, "AAAA")
        self.exit_ok()

    @unittest_run_loop
    async def test_pair_airplay(self):
        self.user_input(str(DEVICE_PIN))
        await self.atvremote(
            "--address", IP_2,
            "--protocol", "airplay",
            "--id", MRP_ID,
            "--airplay-credentials", DEVICE_CREDENTIALS,
            "pair")
        self.has_output("Enter PIN", "seems to have succeeded")
        self.exit_ok()
