"""Functional tests using the API with a fake Apple TV."""

import pyatv
from pyatv.conf import (AirPlayService, MrpService, AppleTV)

from tests import common_functional_tests
from tests.mrp.fake_mrp_atv import (
    FakeAppleTV, AppleTVUseCases)
from tests.airplay.fake_airplay_device import DEVICE_CREDENTIALS


class MRPFunctionalTest(common_functional_tests.CommonFunctionalTests):

    async def setUpAsync(self):
        await super().setUpAsync()
        self.conf = AppleTV('127.0.0.1', 'Test device')
        self.conf.add_service(MrpService('mrp_id', self.fake_atv.port))
        self.conf.add_service(AirPlayService(
            'airplay_id', self.server.port, DEVICE_CREDENTIALS))
        self.atv = await self.get_connected_device()

    async def tearDownAsync(self):
        await self.atv.close()
        await super().tearDownAsync()

    async def get_application(self, loop=None):
        self.fake_atv = FakeAppleTV(self)
        self.usecase = AppleTVUseCases(self.fake_atv)
        await self.fake_atv.start(self.loop)
        return self.fake_atv.app

    async def get_connected_device(self):
        return await pyatv.connect(self.conf, loop=self.loop)
