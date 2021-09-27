"""Functional tests using the API with a fake DMAP Apple TV."""

import asyncio
import ipaddress
import logging

from aiohttp.test_utils import unittest_run_loop

from pyatv import connect, exceptions
from pyatv.conf import AppleTV, ManualService
from pyatv.const import (
    FeatureName,
    FeatureState,
    InputAction,
    OperatingSystem,
    PowerState,
    Protocol,
    RepeatState,
    ShuffleState,
)
from pyatv.protocols.dmap import pairing

from tests import common_functional_tests, zeroconf_stub
from tests.common_functional_tests import DummyDeviceListener
from tests.fake_device import FakeAppleTV
from tests.fake_device.airplay import DEVICE_CREDENTIALS
from tests.utils import until

_LOGGER = logging.getLogger(__name__)

HSGID = "12345678-6789-1111-2222-012345678911"
PAIRING_GUID = "0x0000000000000001"
SESSION_ID = 55555
REMOTE_NAME = "pyatv remote"
PIN_CODE = 1234

ARTWORK_BYTES = b"1234"
ARTWORK_MIMETYPE = "image/png"
AIRPLAY_STREAM = "http://stream"

# This is valid for the PAIR in the pairing module and pin 1234
# (extracted form a real device)
PAIRINGCODE = "690E6FF61E0D7C747654A42AED17047D"

SKIP_TIME = 10


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

    def tearDown(self):
        self.atv.close()
        super().tearDown()

    async def get_application(self, loop=None):
        self.fake_atv = FakeAppleTV(self.loop)
        self.state, self.usecase = self.fake_atv.add_service(
            Protocol.DMAP, hsgid=HSGID, pairing_guid=PAIRING_GUID, session_id=SESSION_ID
        )
        self.airplay_state, self.airplay_usecase = self.fake_atv.add_service(
            Protocol.AirPlay
        )
        return self.fake_atv.app

    async def get_connected_device(self, hsgid):
        self.dmap_service = ManualService("dmapid", Protocol.DMAP, self.server.port, {})
        self.dmap_service.credentials = hsgid
        self.airplay_service = ManualService(
            "airplay_id",
            Protocol.AirPlay,
            self.server.port,
            properties={"features": "0x1"},  # AirPlayVideoV1 supported
        )
        self.airplay_service.credentials = DEVICE_CREDENTIALS
        self.conf = AppleTV(
            ipaddress.IPv4Address("127.0.0.1"),
            "Apple TV",
            properties={"_appletv-v2._tcp.local": {}},
        )
        self.conf.add_service(self.dmap_service)
        self.conf.add_service(self.airplay_service)
        return await connect(self.conf, self.loop)

    @unittest_run_loop
    async def test_app_not_supported(self):
        with self.assertRaises(exceptions.NotSupportedError):
            self.atv.metadata.app

    @unittest_run_loop
    async def test_connect_failed(self):
        # Twice since the client will retry one time
        self.usecase.make_login_fail()
        self.usecase.make_login_fail()

        with self.assertRaises(exceptions.AuthenticationError):
            await self.get_connected_device(HSGID)

    # This test verifies issue #2 (automatic re-login). It uses the artwork
    # API, but it could have been any API since the login code is the same.
    @unittest_run_loop
    async def test_relogin_if_session_expired(self):
        # Here, we are logged in and currently have a asession id. These
        # usescases will result in being logged out (HTTP 403) and forcing a
        # re-login with a new session id (1234)
        self.usecase.example_video()
        self.usecase.force_relogin(1234)
        self.usecase.artwork_no_permission()
        self.usecase.change_artwork(ARTWORK_BYTES, ARTWORK_MIMETYPE)

        artwork = await self.atv.metadata.artwork()
        self.assertEqual(artwork.bytes, ARTWORK_BYTES)

    @unittest_run_loop
    async def test_metadata_artwork_size(self):
        self.usecase.example_video()
        self.usecase.change_artwork(ARTWORK_BYTES, ARTWORK_MIMETYPE)
        await self.playing(title="dummy")

        # DMAP does not indicate dimensions of artwork, so -1 is returned here. In the
        # future, extracting dimensions from PNG header should be feasible.
        artwork = await self.atv.metadata.artwork(width=123, height=456)
        self.assertIsNotNone(artwork)
        self.assertEqual(artwork.width, -1)
        self.assertEqual(artwork.height, -1)

        # Verify that the specified width and height was requested
        self.assertEqual(self.state.last_artwork_width, 123)
        self.assertEqual(self.state.last_artwork_height, 456)

    @unittest_run_loop
    async def test_login_with_pairing_guid_succeed(self):
        self.atv.close()

        # This call will connect and trigger re-login
        await self.get_connected_device(PAIRING_GUID)

    @unittest_run_loop
    async def test_connection_lost(self):
        self.usecase.server_closes_connection()

        device_listener = DummyDeviceListener()
        push_listener = DummyPushListener()
        self.atv.listener = device_listener
        self.atv.push_updater.listener = push_listener
        self.atv.push_updater.start()

        # Callback is scheduled on the event loop, so a semaphore is used
        # to synchronize with the loop
        await asyncio.wait_for(device_listener.lost_sem.acquire(), timeout=3.0)

    @unittest_run_loop
    async def test_button_unsupported_raises(self):
        buttons = ["home", "suspend", "wakeup"]
        for button in buttons:
            with self.assertRaises(exceptions.NotSupportedError):
                await getattr(self.atv.remote_control, button)()

    @unittest_run_loop
    async def test_button_top_menu(self):
        await self.atv.remote_control.top_menu()
        await self.wait_for_button_press("topmenu", InputAction.SingleTap)

    @unittest_run_loop
    async def test_button_play_pause(self):
        await self.atv.remote_control.play_pause()
        await until(lambda: self.state.last_button_pressed == "playpause")

    @unittest_run_loop
    async def test_shuffle_state_albums(self):
        # DMAP does not support "albums" as shuffle state, so it is
        # mapped to "songs"
        self.usecase.example_video(shuffle=ShuffleState.Albums)
        playing = await self.playing(shuffle=ShuffleState.Songs)
        self.assertEqual(playing.shuffle, ShuffleState.Songs)

    @unittest_run_loop
    async def test_set_shuffle_albums(self):
        self.usecase.example_video()

        # DMAP does not support "albums" as shuffle state, so it is
        # mapped to "songs"
        await self.atv.remote_control.set_shuffle(ShuffleState.Albums)
        playing = await self.playing(shuffle=ShuffleState.Songs)
        self.assertEqual(playing.shuffle, ShuffleState.Songs)

    @unittest_run_loop
    async def test_play_url_no_service(self):
        conf = AppleTV("127.0.0.1", "Apple TV")
        conf.add_service(self.dmap_service)

        atv = await connect(conf, self.loop)

        with self.assertRaises(exceptions.NotSupportedError):
            await atv.stream.play_url("http://123")

        atv.close()

    @unittest_run_loop
    async def test_basic_device_info(self):
        self.assertEqual(self.atv.device_info.operating_system, OperatingSystem.Legacy)

    @unittest_run_loop
    async def test_always_available_features(self):
        self.assertFeatures(
            FeatureState.Available,
            FeatureName.Down,
            FeatureName.Left,
            FeatureName.Menu,
            FeatureName.Right,
            FeatureName.Select,
            FeatureName.TopMenu,
            FeatureName.Up,
        )

    @unittest_run_loop
    async def test_unsupported_features(self):
        self.assertFeatures(
            FeatureState.Unsupported,
            FeatureName.Home,
            FeatureName.HomeHold,
            FeatureName.Suspend,
            FeatureName.WakeUp,
            FeatureName.PowerState,
            FeatureName.TurnOn,
            FeatureName.TurnOff,
            FeatureName.App,
        )

    @unittest_run_loop
    async def test_always_unknown_features(self):
        self.assertFeatures(
            FeatureState.Unknown,
            FeatureName.Artwork,
            FeatureName.Next,
            FeatureName.Pause,
            FeatureName.Play,
            FeatureName.PlayPause,
            FeatureName.Previous,
            FeatureName.SetPosition,
            FeatureName.SetRepeat,
            FeatureName.SetShuffle,
            FeatureName.Stop,
            FeatureName.SkipForward,  # Depends on SetPosition
            FeatureName.SkipBackward,  # Depends on SetPosition
        )

    @unittest_run_loop
    async def test_features_shuffle_repeat(self):
        self.usecase.nothing_playing()
        await self.playing()

        self.assertFeatures(
            FeatureState.Unavailable,
            FeatureName.Shuffle,
            FeatureName.Repeat,
        )

        self.usecase.example_music(
            shuffle=ShuffleState.Albums, repeat=RepeatState.Track
        )
        await self.playing(title="music")

        self.assertFeatures(
            FeatureState.Available,
            FeatureName.Shuffle,
            FeatureName.Repeat,
        )

    @unittest_run_loop
    async def test_skip_forward_backward(self):
        self.usecase.example_video()

        prev_position = (await self.playing(title="dummy")).position

        await self.atv.remote_control.skip_forward()
        metadata = await self.playing()
        self.assertEqual(metadata.position, prev_position + SKIP_TIME)
        prev_position = metadata.position

        await self.atv.remote_control.skip_backward()
        metadata = await self.playing()
        self.assertEqual(metadata.position, prev_position - SKIP_TIME)

    @unittest_run_loop
    async def test_reset_revision_if_push_updates_fail(self):
        """Test that revision is reset when an error occurs during push update.

        This test sets up video as playing with revision 0. When the push updater starts,
        that video is returned to the listener. After that, the next update is fetched
        with revision 1. Since no media is configured for that revision, an error occurs
        where new video is configured for revision 0 again (now with "title2" as title),
        which is fetched and returned to the listener.
        """

        class PushListener:
            def __init__(self):
                self.playing = None

            def playstatus_update(self, updater, playstatus):
                _LOGGER.debug("Got playstatus: %s", playstatus)
                self.playing = playstatus

            @staticmethod
            def playstatus_error(updater, exception):
                _LOGGER.warning("Got error: %s", exception)

                # Set new content for revision 0 as an error should reset revision
                self.usecase.example_video(title="video2", revision=0)

        self.usecase.example_video(title="video1", revision=0)

        listener = PushListener()
        self.atv.push_updater.listener = listener
        self.atv.push_updater.start()

        await until(lambda: listener.playing and listener.playing.title == "video2")
        self.assertEqual(listener.playing.title, "video2")
