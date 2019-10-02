"""Functional tests using the API with a fake Apple TV."""

import unittest

from aiohttp.test_utils import unittest_run_loop

from pyatv import connect_to_apple_tv
from pyatv.conf import (AirPlayService, MrpService, AppleTV)

from tests import (common_functional_tests, getmac_stub)
from tests.mrp.fake_mrp_atv import (
    FakeAppleTV, AppleTVUseCases)


@unittest.skip('not ready yet')
class MRPFunctionalTest(common_functional_tests.CommonFunctionalTests):

    async def setUp(self):
        await super().setUpAsync()
        self.atv = await self.get_connected_device(self.fake_atv.port)

    def tearDown(self):
        pass

    async def get_application(self, loop=None):
        self.fake_atv = FakeAppleTV(self)
        self.usecase = AppleTVUseCases(self.fake_atv)
        await self.fake_atv.start(self.loop)
        return self.fake_atv

    async def get_connected_device(self, port):
        conf = AppleTV(getmac_stub.IP, 'Test device')
        conf.add_service(MrpService(port))
        conf.add_service(AirPlayService(self.server.port))
        return await connect_to_apple_tv(conf, loop=self.loop)

    @unittest_run_loop
    def test_dummy_test(self):
        self.assertFalse(True)
