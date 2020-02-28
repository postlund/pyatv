"""Functional tests using the API with a fake Apple TV."""

import logging
from aiohttp.test_utils import unittest_run_loop

import pyatv
from pyatv.const import (
    DeviceState, ShuffleState, PowerState, OperatingSystem)
from pyatv.conf import (AirPlayService, MrpService, AppleTV)

from tests import common_functional_tests
from tests.utils import until, faketime
from tests.mrp.fake_mrp_atv import (
    FakeAppleTV, AppleTVUseCases)
from tests.airplay.fake_airplay_device import DEVICE_CREDENTIALS

_LOGGER = logging.getLogger(__name__)

ARTWORK_BYTES = b'1234'
ARTWORK_MIMETYPE = 'image/png'
ARTWORK_ID = 'artwork_id1'


class MRPFunctionalTest(common_functional_tests.CommonFunctionalTests):

    async def setUpAsync(self):
        await super().setUpAsync()
        self.conf = AppleTV('127.0.0.1', 'Test device')
        self.conf.add_service(MrpService(
            'mrp_id', self.fake_atv.port))
        self.conf.add_service(AirPlayService(
            'airplay_id', self.server.port, DEVICE_CREDENTIALS))
        self.atv = await self.get_connected_device()

    async def tearDownAsync(self):
        await self.atv.close()
        await super().tearDownAsync()

    async def get_application(self, loop=None):
        self.fake_atv = FakeAppleTV(self, self.loop)
        self.usecase = AppleTVUseCases(self.fake_atv)
        return self.fake_atv.app

    async def get_connected_device(self):
        return await pyatv.connect(self.conf, loop=self.loop)

    @unittest_run_loop
    async def test_button_home(self):
        await self.atv.remote_control.home()
        await until(lambda: self.fake_atv.last_button_pressed == 'home')

    @unittest_run_loop
    async def test_button_volume_up(self):
        await self.atv.remote_control.volume_up()
        await until(lambda: self.fake_atv.last_button_pressed == 'volume_up')

    @unittest_run_loop
    async def test_button_volume_down(self):
        await self.atv.remote_control.volume_down()
        await until(lambda: self.fake_atv.last_button_pressed == 'volume_down')

    @unittest_run_loop
    async def test_button_suspend(self):
        await self.atv.remote_control.suspend()
        await until(lambda: self.fake_atv.last_button_pressed == 'suspend')

    @unittest_run_loop
    async def test_button_wakeup(self):
        await self.atv.remote_control.wakeup()
        await until(lambda: self.fake_atv.last_button_pressed == 'wakeup')

    @unittest_run_loop
    async def test_shuffle_state_albums(self):
        self.usecase.example_video(shuffle=ShuffleState.Albums)
        playing = await self.playing(shuffle=ShuffleState.Albums)
        self.assertEqual(playing.shuffle, ShuffleState.Albums)

    @unittest_run_loop
    async def test_set_shuffle_albums(self):
        self.usecase.example_video()

        await self.atv.remote_control.set_shuffle(ShuffleState.Albums)
        playing = await self.playing(shuffle=ShuffleState.Albums)
        self.assertEqual(playing.shuffle, ShuffleState.Albums)

    @unittest_run_loop
    async def test_metadata_artwork_id(self):
        self.usecase.example_video()
        self.usecase.change_artwork(
            ARTWORK_BYTES, ARTWORK_MIMETYPE, ARTWORK_ID)

        await self.playing(title='dummy')
        self.assertEqual(self.atv.metadata.artwork_id, ARTWORK_ID)

    @unittest_run_loop
    async def test_item_updates(self):
        self.usecase.video_playing(
            False, 'dummy', 100, 1, identifier='id', artist='some artist')

        with faketime('pyatv', 0):
            await self.playing(title='dummy')

            # Trigger update of single item by chaging title
            self.usecase.change_metadata(title='foobar', identifier='id')
            playing = await self.playing(title='foobar')

            # Make sure other metadata is untouched
            self.assertEqual(playing.title, 'foobar')
            self.assertEqual(playing.artist, 'some artist')
            self.assertEqual(playing.total_time, 100)
            self.assertEqual(playing.position, 1)

    @unittest_run_loop
    async def test_item_id_hash(self):
        initial_hash = (await self.atv.metadata.playing()).hash

        # Verify thar content identifier is used as hash
        self.usecase.example_video(identifier='some_id')
        playing = await self.playing(title='dummy')
        self.assertEqual(playing.hash, 'some_id')

        # Ensure that we fall back to initial hash if nothing is playing
        self.usecase.nothing_playing()
        nothing_playing = await self.playing(
            device_state=DeviceState.Idle)
        self.assertEqual(nothing_playing.hash, initial_hash)

    @unittest_run_loop
    async def test_metadata_playback_rate_device_state(self):
        self.usecase.example_video()

        playing = await self.playing(title='dummy')
        self.assertEqual(playing.device_state, DeviceState.Paused)

        self.usecase.change_metadata(title='dummy2', playback_rate=1.0)
        playing = await self.playing(title='dummy2')
        self.assertEqual(playing.device_state, DeviceState.Playing)

        self.usecase.change_metadata(title='dummy3', playback_rate=0.0)
        playing = await self.playing(title='dummy3')
        self.assertEqual(playing.device_state, DeviceState.Paused)

    @unittest_run_loop
    async def test_power_state(self):

        class PowerListener():
            def __init__(self):
                self.old_state = None
                self.new_state = None

            def powerstate_update(self, old_state, new_state):
                self.old_state = old_state
                self.new_state = new_state

        listener = PowerListener()
        self.atv.power.listener = listener

        # Check initial power state during connect
        self.assertEqual(self.atv.power.power_state, PowerState.On)

        # Check if power state changes after turn_off command
        await self.atv.power.turn_off()
        await until(lambda: self.atv.power.power_state == PowerState.Off)
        self.assertEqual(listener.old_state, PowerState.On)
        self.assertEqual(listener.new_state, PowerState.Off)

        # Check if power state changes after turn_on command
        await self.atv.power.turn_on()
        await until(lambda: self.atv.power.power_state == PowerState.On)
        self.assertEqual(listener.old_state, PowerState.Off)
        self.assertEqual(listener.new_state, PowerState.On)

    @unittest_run_loop
    async def test_basic_device_info(self):
        self.assertEqual(self.atv.device_info.operating_system,
                         OperatingSystem.TvOS)
