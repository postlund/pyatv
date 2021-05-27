"""Functional tests using the API with a fake Apple TV."""

from ipaddress import IPv4Address
import logging

from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop
from deepdiff import DeepDiff
import pytest

import pyatv
from pyatv import exceptions
from pyatv.companion.server_auth import CLIENT_CREDENTIALS
from pyatv.conf import AppleTV, CompanionService, MrpService
from pyatv.const import Protocol
from pyatv.interface import App, FeatureName, FeatureState

from tests.fake_device import FakeAppleTV
from tests.utils import until

_LOGGER = logging.getLogger(__name__)

TEST_APP: str = "com.test.Test"
TEST_APP_NAME: str = "Test"
TEST_APP2: str = "com.test.Test2"
TEST_APP_NAME2: str = "Test2"


class CompanionFunctionalTest(AioHTTPTestCase):
    async def setUpAsync(self):
        await super().setUpAsync()
        self.conf = AppleTV(IPv4Address("127.0.0.1"), "Test device")
        self.conf.add_service(
            MrpService("mrp_id", self.fake_atv.get_port(Protocol.MRP))
        )
        self.conf.add_service(
            CompanionService(
                self.fake_atv.get_port(Protocol.Companion),
                credentials=CLIENT_CREDENTIALS,
            )
        )
        self.atv = await self.get_connected_device()

    def tearDown(self):
        self.atv.close()
        super().tearDown()

    async def get_application(self, loop=None):
        self.fake_atv = FakeAppleTV(self.loop)
        self.fake_atv.add_service(Protocol.MRP)
        self.state, self.usecase = self.fake_atv.add_service(Protocol.Companion)
        return self.fake_atv.app

    async def get_connected_device(self):
        return await pyatv.connect(self.conf, loop=self.loop)

    @unittest_run_loop
    async def test_connect_only_companion(self):
        conf = AppleTV(IPv4Address("127.0.0.1"), "Test device")
        conf.add_service(CompanionService(self.fake_atv.get_port(Protocol.Companion)))

        with pytest.raises(exceptions.DeviceIdMissingError):
            await pyatv.connect(conf, loop=self.loop)

    @unittest_run_loop
    async def test_launch_app(self):
        await self.atv.apps.launch_app(TEST_APP)
        await until(lambda: self.state.active_app == TEST_APP)

    @unittest_run_loop
    async def test_app_list(self):
        self.usecase.set_installed_apps(
            {
                TEST_APP: TEST_APP_NAME,
                TEST_APP2: TEST_APP_NAME2,
            }
        )

        apps = await self.atv.apps.app_list()

        expected_apps = [App(TEST_APP_NAME, TEST_APP), App(TEST_APP_NAME2, TEST_APP2)]
        assert not DeepDiff(expected_apps, apps)

    @unittest_run_loop
    async def test_features(self):
        assert (
            self.atv.features.get_feature(FeatureName.LaunchApp).state
            == FeatureState.Available
        )
        assert (
            self.atv.features.get_feature(FeatureName.AppList).state
            == FeatureState.Available
        )

    @unittest_run_loop
    async def test_power_functions(self):
        assert self.state.powered_on

        await self.atv.power.turn_off()
        assert not self.state.powered_on

        await self.atv.power.turn_on()
        assert self.state.powered_on

    @unittest_run_loop
    async def test_session_start(self):
        # All commands should trigger a session start, so just use one and verify
        assert self.state.sid == 0
        await self.atv.power.turn_off()
        assert self.state.sid != 0
        assert self.state.service_type == "com.apple.tvremoteservices"
