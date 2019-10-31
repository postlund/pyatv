"""Functional tests using the API with a fake Apple TV."""

import unittest

from aiohttp.test_utils import unittest_run_loop

import pyatv
from pyatv.conf import (AirPlayService, MrpService, AppleTV)

from tests import common_functional_tests
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
        conf = AppleTV('127.0.0.1', 'Test device')
        conf.add_service(MrpService('mrp_id', port))
        conf.add_service(AirPlayService('airplay_id', self.server.port))
        return await pyatv.connect(conf, loop=self.loop)

    @unittest_run_loop
    def test_dummy_test(self):
        self.assertFalse(True)
