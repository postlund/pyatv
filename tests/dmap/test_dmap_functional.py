"""Functional tests using the API with a fake DMAP Apple TV."""

import asyncio
import ipaddress

from aiohttp.test_utils import unittest_run_loop

import pyatv
from pyatv import exceptions, interface
from pyatv.conf import (AirPlayService, DmapService, AppleTV)
from pyatv.const import MediaType, DeviceState, RepeatState
from pyatv.dmap import pairing
from tests.dmap.fake_dmap_atv import (FakeAppleTV, AppleTVUseCases)
from tests.airplay.fake_airplay_device import DEVICE_CREDENTIALS
from tests import (zeroconf_stub, common_functional_tests)

HSGID = '12345-6789-0'
PAIRING_GUID = '0x0000000000000001'
SESSION_ID = 55555
REMOTE_NAME = 'pyatv remote'
PIN_CODE = 1234

ARTWORK_BYTES = b'1234'
ARTWORK_MIMETYPE = 'image/png'
AIRPLAY_STREAM = 'http://stream'

# This is valid for the PAIR in the pairing module and pin 1234
# (extracted form a real device)
PAIRINGCODE = '690E6FF61E0D7C747654A42AED17047D'

HOMESHARING_SERVICE_1 = zeroconf_stub.homesharing_service(
    'AAAA', b'Apple TV 1', '10.0.0.1', b'aaaa')
HOMESHARING_SERVICE_2 = zeroconf_stub.homesharing_service(
    'BBBB', b'Apple TV 2', '10.0.0.2', b'bbbb')


class DummyDeviceListener(interface.DeviceListener):

    def __init__(self):
        self.closed_sem = asyncio.Semaphore(0)
        self.lost_sem = asyncio.Semaphore(0)

    def connection_lost(self, exception):
        self.lost_sem.release()

    def connection_closed(self):
        self.closed_sem.release()


class DummyPushListener:

    @staticmethod
    def playstatus_update(updater, playstatus):
        updater.stop()

    @staticmethod
    def playstatus_error(updater, exception):
        pass


class DMAPFunctionalTest(common_functional_tests.CommonFunctionalTests):

    async def setUpAsync(self):
        await super().setUpAsync()
        self.atv = await self.get_connected_device(HSGID)

        # TODO: currently stubs internal method, should provide stub
        # for netifaces later
        pairing._get_private_ip_addresses = \
            lambda: [ipaddress.ip_address('10.0.0.1')]

    async def tearDownAsync(self):
        await self.atv.close()
        await super().tearDownAsync()

    async def get_application(self, loop=None):
        self.fake_atv = FakeAppleTV(
            HSGID, PAIRING_GUID, SESSION_ID, self)
        self.usecase = AppleTVUseCases(self.fake_atv)
        return self.fake_atv.app

    async def get_connected_device(self, hsgid):
        self.dmap_service = DmapService(
            'dmap_id', hsgid, port=self.server.port)
        self.airplay_service = AirPlayService(
            'airplay_id', self.server.port, DEVICE_CREDENTIALS)
        self.conf = AppleTV('127.0.0.1', 'Apple TV')
        self.conf.add_service(self.dmap_service)
        self.conf.add_service(self.airplay_service)
        return await pyatv.connect(self.conf, self.loop)

    @unittest_run_loop
    async def test_not_supportedt(self):
        with self.assertRaises(exceptions.NotSupportedError):
            await self.atv.remote_control.suspend()

    @unittest_run_loop
    async def test_connect_failed(self):
        # Twice since the client will retry one time
        self.usecase.make_login_fail()
        self.usecase.make_login_fail()

        with self.assertRaises(exceptions.AuthenticationError):
            await self.atv.connect()

    # This test verifies issue #2 (automatic re-login). It uses the artwork
    # API, but it could have been any API since the login code is the same.
    @unittest_run_loop
    async def test_relogin_if_session_expired(self):
        await self.atv.connect()

        # Here, we are logged in and currently have a asession id. These
        # usescases will result in being logged out (HTTP 403) and forcing a
        # re-login with a new session id (1234)
        self.usecase.force_relogin(1234)
        self.usecase.artwork_no_permission()
        self.usecase.change_artwork(ARTWORK_BYTES, ARTWORK_MIMETYPE)

        artwork = await self.atv.metadata.artwork()
        self.assertEqual(artwork.bytes, ARTWORK_BYTES)

    @unittest_run_loop
    async def test_login_with_hsgid_succeed(self):
        session_id = await self.atv.connect()
        self.assertEqual(SESSION_ID, session_id)

    @unittest_run_loop
    async def test_login_with_pairing_guid_succeed(self):
        await self.atv.close()
        self.atv = await self.get_connected_device(PAIRING_GUID)
        session_id = await self.atv.connect()
        self.assertEqual(SESSION_ID, session_id)

    @unittest_run_loop
    async def test_connection_closed(self):
        self.usecase.video_playing(paused=False, title='video1',
                                   total_time=40, position=10,
                                   revision=0)

        self.atv.listener = DummyDeviceListener()
        self.atv.push_updater.listener = DummyPushListener()
        await self.atv.push_updater.start()

        # Callback is scheduled on the event loop, so a semaphore is used
        # to synchronize with the loop
        await asyncio.wait_for(
            self.atv.listener.closed_sem.acquire(), timeout=3.0)

    @unittest_run_loop
    async def test_connection_lost(self):
        self.usecase.server_closes_connection()

        self.atv.listener = DummyDeviceListener()
        self.atv.push_updater.listener = DummyPushListener()
        await self.atv.push_updater.start()

        # Callback is scheduled on the event loop, so a semaphore is used
        # to synchronize with the loop
        await asyncio.wait_for(
            self.atv.listener.lost_sem.acquire(), timeout=3.0)

    # Common tests are below. Move tests that have been implemented to
    # common_functional_tests.py once implemented

    # TODO: This should check that device_id is one of the IDs
    #       passed to the services into the device.
    def test_metadata_device_id(self):
        self.assertEqual(self.atv.metadata.device_id, 'dmap_id')

    @unittest_run_loop
    async def test_metadata_artwork(self):
        self.usecase.change_artwork(ARTWORK_BYTES, ARTWORK_MIMETYPE)

        artwork = await self.atv.metadata.artwork()
        self.assertIsNotNone(artwork)
        self.assertEqual(artwork.bytes, ARTWORK_BYTES)
        self.assertEqual(artwork.mimetype, ARTWORK_MIMETYPE)

    @unittest_run_loop
    async def test_metadata_artwork_none_if_not_available(self):
        self.usecase.change_artwork(b'', None)

        artwork = await self.atv.metadata.artwork()
        self.assertIsNone(artwork)

    @unittest_run_loop
    async def test_metadata_none_type_when_not_playing(self):
        self.usecase.nothing_playing()

        playing = await self.atv.metadata.playing()
        self.assertEqual(playing.media_type, MediaType.Unknown)
        self.assertEqual(playing.device_state, DeviceState.Idle)

    @unittest_run_loop
    async def test_metadata_video_playing(self):
        self.usecase.video_playing(paused=False, title='video',
                                   total_time=40, position=10)

        playing = await self.atv.metadata.playing()
        self.assertEqual(playing.media_type, MediaType.Video)
        self.assertEqual(playing.device_state, DeviceState.Playing)
        self.assertEqual(playing.title, 'video')
        self.assertEqual(playing.total_time, 40)
        self.assertEqual(playing.position, 10)

    @unittest_run_loop
    async def test_metadata_music_paused(self):
        self.usecase.music_playing(paused=True, title='music',
                                   artist='artist', album='album',
                                   total_time=222, position=49,
                                   genre='genre')

        playing = await self.atv.metadata.playing()
        self.assertEqual(playing.media_type, MediaType.Music)
        self.assertEqual(playing.device_state, DeviceState.Paused)
        self.assertEqual(playing.title, 'music')
        self.assertEqual(playing.artist, 'artist')
        self.assertEqual(playing.album, 'album')
        self.assertEqual(playing.genre, 'genre')
        self.assertEqual(playing.total_time, 222)
        self.assertEqual(playing.position, 49)

    @unittest_run_loop
    async def test_metadata_music_playing(self):
        self.usecase.music_playing(paused=False, title='music',
                                   artist='test1', album='test2',
                                   total_time=2, position=1,
                                   genre='genre')

        playing = await self.atv.metadata.playing()
        self.assertEqual(playing.media_type, MediaType.Music)
        self.assertEqual(playing.device_state, DeviceState.Playing)
        self.assertEqual(playing.title, 'music')
        self.assertEqual(playing.artist, 'test1')
        self.assertEqual(playing.album, 'test2')
        self.assertEqual(playing.genre, 'genre')
        self.assertEqual(playing.total_time, 2)
        self.assertEqual(playing.position, 1)

    @unittest_run_loop
    async def test_push_updates(self):

        class PushListener:
            def __init__(self):
                self.playing = None

            def playstatus_update(self, updater, playstatus):
                self.playing = playstatus
                updater.stop()

            @staticmethod
            def playstatus_error(updater, exception):
                pass

        # Prepare two playstatus updates in the fake device. Take note: every
        # time start() is called, revision 0 should be used first. This will
        # make sure that we always get a push update instantly. Otherwise we
        # might hang and wait for an update.
        self.usecase.video_playing(paused=False, title='video1',
                                   total_time=40, position=10,
                                   revision=0)
        self.usecase.video_playing(paused=True, title='video2',
                                   total_time=30, position=20,
                                   revision=0)

        # Poll the first one ("video1")
        await self.atv.metadata.playing()

        # Setup push updates which will instantly get the next one ("video2")
        listener = PushListener()
        self.atv.push_updater.listener = listener
        await self.atv.push_updater.start()

        # Check that we got the right one
        self.assertIsNotNone(listener.playing)
        self.assertEqual(listener.playing.title, 'video2')

    @unittest_run_loop
    async def test_shuffle_state(self):
        self.usecase.example_video(shuffle=False)
        self.usecase.example_video(shuffle=True)

        playing = await self.atv.metadata.playing()
        self.assertFalse(playing.shuffle)

        playing = await self.atv.metadata.playing()
        self.assertTrue(playing.shuffle)

    @unittest_run_loop
    async def test_repeat_state(self):
        self.usecase.example_video(repeat=RepeatState.Off)
        self.usecase.example_video(repeat=RepeatState.Track)
        self.usecase.example_video(repeat=RepeatState.All)

        playing = await self.atv.metadata.playing()
        self.assertEqual(playing.repeat, RepeatState.Off)

        playing = await self.atv.metadata.playing()
        self.assertEqual(playing.repeat, RepeatState.Track)

        playing = await self.atv.metadata.playing()
        self.assertEqual(playing.repeat, RepeatState.All)

    @unittest_run_loop
    async def test_set_shuffle(self):
        await self.atv.remote_control.set_shuffle(1)
        self.assertEqual(self.fake_atv.properties['dacp.shufflestate'], 1)

        await self.atv.remote_control.set_shuffle(0)
        self.assertEqual(self.fake_atv.properties['dacp.shufflestate'], 0)

    @unittest_run_loop
    async def test_set_repeat(self):
        await self.atv.remote_control.set_repeat(1)
        self.assertEqual(self.fake_atv.properties['dacp.repeatstate'], 1)

        await self.atv.remote_control.set_repeat(2)
        self.assertEqual(self.fake_atv.properties['dacp.repeatstate'], 2)

    @unittest_run_loop
    async def test_seek_in_playing_media(self):
        await self.atv.remote_control.set_position(60)
        self.assertEqual(self.fake_atv.properties['dacp.playingtime'], 60000)

    @unittest_run_loop
    async def test_metadata_loading(self):
        self.usecase.media_is_loading()

        playing = await self.atv.metadata.playing()
        self.assertEqual(playing.device_state, DeviceState.Loading)

    @unittest_run_loop
    async def test_button_unsupported_raises(self):
        buttons = ['home', 'volume_up', 'volume_down', 'suspend', 'wakeup']
        for button in buttons:
            with self.assertRaises(exceptions.NotSupportedError):
                await getattr(self.atv.remote_control, button)()
