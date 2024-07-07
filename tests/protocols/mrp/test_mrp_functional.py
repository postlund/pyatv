"""Functional tests using the API with a fake Apple TV."""

import asyncio
from ipaddress import IPv4Address
import logging
import math
from typing import Optional

import pyatv
from pyatv.conf import AppleTV, ManualService
from pyatv.const import (
    DeviceModel,
    DeviceState,
    FeatureName,
    FeatureState,
    InputAction,
    MediaType,
    OperatingSystem,
    PowerState,
    Protocol,
    ShuffleState,
)
from pyatv.interface import OutputDevice
from pyatv.protocols.mrp.protobuf import CommandInfo_pb2
from pyatv.support.http import (
    BasicHttpServer,
    HttpRequest,
    HttpResponse,
    HttpSimpleRouter,
    http_server,
)

from tests import common_functional_tests
from tests.fake_device import FakeAppleTV
from tests.fake_device.airplay import DEVICE_CREDENTIALS
from tests.fake_device.mrp import (
    APP_NAME,
    BUILD_NUMBER,
    DEVICE_MODEL,
    DEVICE_UID,
    OS_VERSION,
    PLAYER_IDENTIFIER,
    VOLUME_STEP,
)
from tests.utils import faketime, stub_sleep, until

_LOGGER = logging.getLogger(__name__)

ARTWORK_BYTES = b"1234"
ARTWORK_MIMETYPE = "image/png"
ARTWORK_ID = "artwork_id1"

DEMO_APP_NAME = "Demo App"

TEST_PLAYER = "com.github.postlund.test"


class MRPFunctionalTest(common_functional_tests.CommonFunctionalTests):
    async def setUpAsync(self):
        await super().setUpAsync()
        self.conf = AppleTV(IPv4Address("127.0.0.1"), "Test device")
        self.conf.add_service(
            ManualService(
                "mrp_id", Protocol.MRP, self.fake_atv.get_port(Protocol.MRP), {}
            )
        )
        airplay_service = ManualService(
            "airplay_id",
            Protocol.AirPlay,
            self.fake_atv.get_port(Protocol.AirPlay),
            properties={"features": "0x1"},  # AirPlayVideoV1 supported
        )
        airplay_service.credentials = DEVICE_CREDENTIALS
        self.conf.add_service(airplay_service)
        self.atv = await self.get_connected_device()
        self.artwork_server = None

    async def tearDownAsync(self):
        await asyncio.gather(*self.atv.close())
        if self.artwork_server is not None:
            self.artwork_server.close()
        await super().tearDownAsync()

    async def get_application(self, loop=None):
        self.fake_atv = FakeAppleTV(self.loop)
        self.state, self.usecase = self.fake_atv.add_service(Protocol.MRP)
        self.airplay_state, self.airplay_usecase = self.fake_atv.add_service(
            Protocol.AirPlay
        )
        return self.fake_atv.app

    async def get_connected_device(self):
        return await pyatv.connect(self.conf, loop=self.loop)

    def supported_volume_controls(self):
        return [
            FeatureName.VolumeUp,
            FeatureName.VolumeDown,
            FeatureName.Volume,
            FeatureName.SetVolume,
        ]

    async def serve_artwork(self, path: str) -> int:
        class ArtworkHandler(HttpSimpleRouter):
            def __init__(self, path: str):
                super().__init__()
                self.add_route("GET", path, self.handle_artwork)

            def handle_artwork(self, request: HttpRequest) -> Optional[HttpResponse]:
                return HttpResponse(
                    "HTTP",
                    "1.0",
                    200,
                    "OK",
                    {"Content-Type": ARTWORK_MIMETYPE},
                    ARTWORK_BYTES,
                )

        self.artwork_server, port = await http_server(
            lambda: BasicHttpServer(ArtworkHandler(path))
        )
        return port

    async def test_button_up_actions(self):
        await self.atv.remote_control.up(action=InputAction.DoubleTap)
        await self.wait_for_button_press("up", InputAction.DoubleTap)

        await self.atv.remote_control.up(action=InputAction.Hold)
        await self.wait_for_button_press("up", InputAction.Hold)

    async def test_button_down_actions(self):
        await self.atv.remote_control.down(action=InputAction.DoubleTap)
        await self.wait_for_button_press("down", InputAction.DoubleTap)

        await self.atv.remote_control.down(action=InputAction.Hold)
        await self.wait_for_button_press("down", InputAction.Hold)

    async def test_button_left_actions(self):
        await self.atv.remote_control.left(action=InputAction.DoubleTap)
        await self.wait_for_button_press("left", InputAction.DoubleTap)

        await self.atv.remote_control.left(action=InputAction.Hold)
        await self.wait_for_button_press("left", InputAction.Hold)

    async def test_button_right_actions(self):
        await self.atv.remote_control.right(action=InputAction.DoubleTap)
        await self.wait_for_button_press("right", InputAction.DoubleTap)

        await self.atv.remote_control.right(action=InputAction.Hold)
        await self.wait_for_button_press("right", InputAction.Hold)

    async def test_button_top_menu(self):
        await self.atv.remote_control.top_menu()
        await self.wait_for_button_press("top_menu", InputAction.SingleTap)

    async def test_button_home(self):
        await self.atv.remote_control.home()
        await self.wait_for_button_press("home", InputAction.SingleTap)

        await self.atv.remote_control.home(action=InputAction.DoubleTap)
        await self.wait_for_button_press("home", InputAction.DoubleTap)

        await self.atv.remote_control.home(action=InputAction.Hold)
        await self.wait_for_button_press("home", InputAction.Hold)

    async def test_button_home_hold(self):
        await self.atv.remote_control.home_hold()
        await self.wait_for_button_press("home", InputAction.Hold)

    async def test_button_select_actions(self):
        await self.atv.remote_control.select(action=InputAction.DoubleTap)
        await self.wait_for_button_press("select", InputAction.DoubleTap)

        await self.atv.remote_control.select(action=InputAction.Hold)
        await self.wait_for_button_press("select", InputAction.Hold)

    async def test_button_menu_actions(self):
        await self.atv.remote_control.menu(action=InputAction.DoubleTap)
        await self.wait_for_button_press("menu", InputAction.DoubleTap)

        await self.atv.remote_control.menu(action=InputAction.Hold)
        await self.wait_for_button_press("menu", InputAction.Hold)

    async def test_button_suspend(self):
        await self.atv.remote_control.suspend()
        await until(lambda: self.state.last_button_pressed == "suspend")

    async def test_button_wakeup(self):
        await self.atv.remote_control.wakeup()
        await until(lambda: self.state.last_button_pressed == "wakeup")

    async def test_shuffle_state_albums(self):
        self.usecase.example_video(shuffle=ShuffleState.Albums)
        playing = await self.playing(shuffle=ShuffleState.Albums)
        self.assertEqual(playing.shuffle, ShuffleState.Albums)

    async def test_set_shuffle_albums(self):
        self.usecase.example_video()

        await self.atv.remote_control.set_shuffle(ShuffleState.Albums)
        playing = await self.playing(shuffle=ShuffleState.Albums)
        self.assertEqual(playing.shuffle, ShuffleState.Albums)

    async def test_metadata_artwork_id(self):
        self.usecase.example_video()
        self.usecase.change_artwork(ARTWORK_BYTES, ARTWORK_MIMETYPE, ARTWORK_ID)

        await self.playing(title="dummy")
        self.assertEqual(self.atv.metadata.artwork_id, ARTWORK_ID)

    async def test_metadata_artwork_id_no_identifier(self):
        self.usecase.example_video(identifier="some_id")
        self.usecase.change_artwork(ARTWORK_BYTES, ARTWORK_MIMETYPE, None)

        await self.playing(title="dummy")
        self.assertEqual(self.atv.metadata.artwork_id, "some_id")

    async def test_metadata_artwork_erroneously_available(self):
        self.usecase.example_video()

        # Metadata suggests that artwork is available but no artwork is available
        # when requested by client
        self.usecase.change_artwork(None, ARTWORK_MIMETYPE, ARTWORK_ID)

        await self.playing(title="dummy")

        artwork = await self.atv.metadata.artwork(width=123, height=456)
        self.assertIsNone(artwork)

    async def test_metadata_artwork_width_and_height(self):
        self.usecase.example_video()
        self.usecase.change_artwork(
            ARTWORK_BYTES, ARTWORK_MIMETYPE, width=111, height=222
        )

        await self.playing(title="dummy")

        # Request one size but simulate that a smaller artwork was returned
        artwork = await self.atv.metadata.artwork(width=123, height=456)
        self.assertEqual(artwork.width, 111)
        self.assertEqual(artwork.height, 222)

    async def test_metadata_artwork_url(self):
        port = await self.serve_artwork("/test")

        self.usecase.example_video()
        self.usecase.change_artwork(b"", "", url=f"http://localhost:{port}/test")

        await self.playing(title="dummy")

        artwork = await self.atv.metadata.artwork(width=123, height=456)
        self.assertEqual(artwork.bytes, ARTWORK_BYTES)
        self.assertEqual(artwork.mimetype, ARTWORK_MIMETYPE)

    async def test_metadata_artwork_url_in_identifier(self):
        port = await self.serve_artwork("/test/123x456bb.png")

        self.usecase.example_video()
        self.usecase.change_artwork(
            b"",
            "",
            identifier=f"http://localhost:{port}/test/{{w}}x{{h}}{{c}}.{{f}}",
            url=f"http://localhost:{port}/test/1200x1200bb.heic",
        )

        await self.playing(title="dummy")

        artwork = await self.atv.metadata.artwork(width=123, height=456)
        self.assertEqual(artwork.bytes, ARTWORK_BYTES)
        self.assertEqual(artwork.mimetype, ARTWORK_MIMETYPE)

    async def test_item_updates(self):
        self.usecase.video_playing(
            False, "dummy", 100, 1, identifier="id", artist="some artist"
        )

        with faketime("pyatv", 0):
            await self.playing(title="dummy")

            # Trigger update of single item by changing title
            self.usecase.change_metadata(title="foobar", identifier="id")
            playing = await self.playing(title="foobar")

            # Make sure other metadata is untouched
            self.assertEqual(playing.title, "foobar")
            self.assertEqual(playing.artist, "some artist")
            self.assertEqual(playing.total_time, 100)
            self.assertEqual(playing.position, 1)

    async def test_item_id_hash(self):
        initial_hash = (await self.atv.metadata.playing()).hash

        # Verify that content identifier is used as hash
        self.usecase.example_video(identifier="some_id")
        playing = await self.playing(title="dummy")
        self.assertEqual(playing.hash, "some_id")

        # Ensure that we fall back to initial hash if nothing is playing
        self.usecase.nothing_playing()
        nothing_playing = await self.playing(device_state=DeviceState.Idle)
        self.assertEqual(nothing_playing.hash, initial_hash)

    async def test_metadata_playback_rate_device_state(self):
        self.usecase.example_video(paused=False, playback_rate=0.0)

        playing = await self.playing(title="dummy")
        self.assertEqual(playing.device_state, DeviceState.Playing)

        self.usecase.change_metadata(title="dummy2", playback_rate=1.0)
        playing = await self.playing(title="dummy2")
        self.assertEqual(playing.device_state, DeviceState.Playing)

        self.usecase.example_video(paused=True, title="dummy3", playback_rate=0.0)
        playing = await self.playing(title="dummy3")
        self.assertEqual(playing.device_state, DeviceState.Paused)

    async def test_power_state(self):
        class PowerListener:
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
        assert math.isclose(stub_sleep(), 0.1)
        await until(lambda: self.atv.power.power_state == PowerState.Off)
        await until(lambda: listener.old_state == PowerState.On)
        await until(lambda: listener.new_state == PowerState.Off)

        # Check if power state changes after turn_on command
        await self.atv.power.turn_on()
        await until(lambda: self.atv.power.power_state == PowerState.On)
        await until(lambda: listener.old_state == PowerState.Off)
        await until(lambda: listener.new_state == PowerState.On)

    async def test_power_state_acknowledgement(self):
        self.assertEqual(self.atv.power.power_state, PowerState.On)
        await self.atv.power.turn_off(await_new_state=True)
        self.assertEqual(self.atv.power.power_state, PowerState.Off)
        await self.atv.power.turn_on(await_new_state=True)
        self.assertEqual(self.atv.power.power_state, PowerState.On)

    async def test_basic_device_info(self):
        self.assertEqual(self.atv.device_info.operating_system, OperatingSystem.TvOS)
        self.assertEqual(self.atv.device_info.build_number, BUILD_NUMBER)
        self.assertEqual(self.atv.device_info.version, OS_VERSION)
        self.assertEqual(self.atv.device_info.raw_model, DEVICE_MODEL)
        self.assertEqual(self.atv.device_info.model, DeviceModel.Gen4K)

    async def test_always_available_features(self):
        self.assertFeatures(
            FeatureState.Available,
            FeatureName.Down,
            FeatureName.Home,
            FeatureName.HomeHold,
            FeatureName.Left,
            FeatureName.Menu,
            FeatureName.Right,
            FeatureName.Select,
            FeatureName.TopMenu,
            FeatureName.Up,
            FeatureName.TurnOn,
            FeatureName.TurnOff,
            FeatureName.PowerState,
            FeatureName.OutputDevices,
            FeatureName.AddOutputDevices,
            FeatureName.RemoveOutputDevices,
            FeatureName.SetOutputDevices,
        )

    async def test_features_artwork(self):
        self.assertFeatures(FeatureState.Unavailable, FeatureName.Artwork)

        self.usecase.example_video()
        self.usecase.change_artwork(ARTWORK_BYTES, ARTWORK_MIMETYPE, ARTWORK_ID)
        await self.playing(title="dummy")

        self.assertFeatures(FeatureState.Available, FeatureName.Artwork)

    async def test_features_with_supported_commands(self):
        feature_map = {
            FeatureName.Next: CommandInfo_pb2.NextTrack,
            FeatureName.Pause: CommandInfo_pb2.Pause,
            FeatureName.Play: CommandInfo_pb2.Play,
            FeatureName.PlayPause: CommandInfo_pb2.TogglePlayPause,
            FeatureName.Previous: CommandInfo_pb2.PreviousTrack,
            FeatureName.Stop: CommandInfo_pb2.Stop,
            FeatureName.SetPosition: CommandInfo_pb2.SeekToPlaybackPosition,
            FeatureName.SetRepeat: CommandInfo_pb2.ChangeRepeatMode,
            FeatureName.SetShuffle: CommandInfo_pb2.ChangeShuffleMode,
            FeatureName.Shuffle: CommandInfo_pb2.ChangeShuffleMode,
            FeatureName.Repeat: CommandInfo_pb2.ChangeRepeatMode,
            FeatureName.SkipForward: CommandInfo_pb2.SkipForward,
            FeatureName.SkipBackward: CommandInfo_pb2.SkipBackward,
        }

        # No supported commands by default
        self.usecase.example_video()
        await self.playing(title="dummy")
        self.assertFeatures(FeatureState.Unavailable, *feature_map.keys())

        # Inject all expected commands to be enabled
        self.usecase.example_video(
            title="dummy2", supported_commands=list(feature_map.values())
        )
        await self.playing(title="dummy2")
        self.assertFeatures(FeatureState.Available, *feature_map.keys())

    async def test_playing_app(self):
        self.usecase.nothing_playing()

        # Nothing playing => no app running
        self.assertIsNone(self.atv.metadata.app)
        self.assertEqual(
            self.atv.features.get_feature(FeatureName.App).state,
            FeatureState.Unavailable,
        )

        self.usecase.example_video()
        await self.playing(title="dummy")

        # Video playing with default app
        self.assertEqual(self.atv.metadata.app.name, APP_NAME)
        self.assertEqual(self.atv.metadata.app.identifier, PLAYER_IDENTIFIER)
        self.assertEqual(
            self.atv.features.get_feature(FeatureName.App).state, FeatureState.Available
        )

        # Change app display_name name
        self.usecase.update_client(display_name=DEMO_APP_NAME)
        self.usecase.change_metadata(title="dummy2")
        await self.playing(title="dummy2")
        self.assertEqual(self.atv.metadata.app.name, DEMO_APP_NAME)

        # Do not include display name and reuse previous one
        self.usecase.update_client(display_name=None)
        self.usecase.change_metadata(title="dummy3")
        await self.playing(title="dummy3")
        self.assertEqual(self.atv.metadata.app.name, DEMO_APP_NAME)

    async def test_skip_forward_backward(self):
        self.usecase.example_video(
            supported_commands=[
                CommandInfo_pb2.SkipForward,
                CommandInfo_pb2.SkipBackward,
            ],
            skip_time=12,
        )

        # Get initial position and use as base
        prev_position = (await self.playing(title="dummy")).position

        await self.atv.remote_control.skip_forward()
        self.usecase.change_metadata(title="dummy2")
        metadata = await self.playing(title="dummy2")
        self.assertEqual(metadata.position, prev_position + 12)
        prev_position = metadata.position

        # Change skip time 8 to verify that we respect provided values
        self.usecase.change_state(title="dummy3", skip_time=8)
        metadata = await self.playing(title="dummy3")

        await self.atv.remote_control.skip_backward()
        self.usecase.change_metadata(title="dummy4")
        metadata = await self.playing(title="dummy4")
        self.assertEqual(metadata.position, prev_position - 8)
        prev_position = metadata.position

        # Test specified skip time
        await self.atv.remote_control.skip_forward(17)
        self.usecase.change_metadata(title="dummy5")
        metadata = await self.playing(title="dummy5")
        self.assertEqual(metadata.position, prev_position + 17)

    async def test_button_play_pause(self):
        self.usecase.example_video(supported_commands=[CommandInfo_pb2.TogglePlayPause])

        await self.playing(title="dummy")
        await self.atv.remote_control.play_pause()
        await until(lambda: self.state.last_button_pressed == "playpause")

    async def test_play_pause_emulation(self):
        self.usecase.example_video(paused=False)
        await self.playing(device_state=DeviceState.Playing)
        self.assertFeatures(FeatureState.Unavailable, FeatureName.PlayPause)

        await self.atv.remote_control.play_pause()
        await until(lambda: self.state.last_button_pressed == "pause")

        self.usecase.example_video(
            paused=True,
            supported_commands=[CommandInfo_pb2.Play, CommandInfo_pb2.Pause],
        )
        await self.playing(device_state=DeviceState.Paused)
        self.assertFeatures(FeatureState.Available, FeatureName.PlayPause)

        await self.atv.remote_control.play_pause()
        await until(lambda: self.state.last_button_pressed == "play")

    async def test_update_client_before_setstate(self):
        self.usecase.update_client(APP_NAME, TEST_PLAYER)
        self.usecase.example_video(title="test", player=TEST_PLAYER, app_name=None)

        await self.playing(title="test")
        self.assertEqual(self.atv.metadata.app.name, APP_NAME)
        self.assertEqual(self.atv.metadata.app.identifier, TEST_PLAYER)

    async def test_set_default_commands(self):
        self.usecase.default_supported_commands(
            [CommandInfo_pb2.Play, CommandInfo_pb2.Pause]
        )
        self.usecase.example_video()

        await self.playing(title="dummy")
        self.assertFeatures(FeatureState.Available, FeatureName.Play, FeatureName.Pause)

    async def test_playing_immutable_update_content_item(self):
        self.usecase.example_video(position=1)
        playing = await self.playing(title="dummy")

        self.usecase.change_metadata(position=100)
        await self.playing(position=100)

        self.assertEqual(playing.position, 1)

    async def test_metadata_tv_playing(self):
        self.usecase.tv_playing(
            paused=False,
            series_name="tv",
            total_time=40,
            position=10,
            season_number=12,
            episode_number=4,
            content_identifier="identifier",
            itunes_store_identifier=123456789,
        )

        with faketime("pyatv", 0):
            playing = await self.playing(series_name="tv")
            self.assertEqual(playing.media_type, MediaType.Video)
            self.assertEqual(playing.device_state, DeviceState.Playing)
            self.assertEqual(playing.series_name, "tv")
            self.assertEqual(playing.total_time, 40)
            self.assertEqual(playing.position, 10)
            self.assertEqual(playing.season_number, 12)
            self.assertEqual(playing.episode_number, 4)
            self.assertEqual(playing.content_identifier, "identifier")
            self.assertEqual(playing.itunes_store_identifier, 123456789)

        self.assertFeatures(
            FeatureState.Available,
            FeatureName.SeriesName,
            FeatureName.TotalTime,
            FeatureName.Position,
            FeatureName.SeasonNumber,
            FeatureName.EpisodeNumber,
            FeatureName.ContentIdentifier,
        )

    async def test_absolute_volume_features(self):
        features = [
            FeatureName.Volume,
            FeatureName.SetVolume,
        ]
        self.assertFeatures(FeatureState.Unavailable, *features)

        self.usecase.change_volume_control(
            available=True, support_absolute=False, support_relative=True
        )
        self.usecase.example_video(title="dummy2")
        await self.playing(title="dummy2")
        self.assertFeatures(FeatureState.Unavailable, *features)

        self.usecase.change_volume_control(
            available=True, support_absolute=True, support_relative=False
        )
        self.usecase.example_video(title="dummy3")
        await self.playing(title="dummy3")
        self.assertFeatures(FeatureState.Available, *features)

        self.usecase.change_volume_control(
            available=True, support_absolute=True, support_relative=True
        )
        self.usecase.example_video(title="dummy4")
        await self.playing(title="dummy4")
        self.assertFeatures(FeatureState.Available, *features)

    async def test_volume_change(self):
        self.usecase.change_volume_control(available=True)

        await until(lambda: math.isclose(self.atv.audio.volume, 0.0))

        await until(
            lambda: self.atv.features.in_state(
                FeatureState.Available, FeatureName.SetVolume
            )
        )

        # Manually set a new volume level
        await self.atv.audio.set_volume(20.0)
        await until(lambda: math.isclose(self.atv.audio.volume, 20.0))

        # Trigger volume change from device
        self.usecase.set_volume(0.3, DEVICE_UID)
        await until(lambda: math.isclose(self.atv.audio.volume, 30.0))

    async def _test_audio_volume_up_increases_volume(self):
        await until(
            lambda: self.atv.features.in_state(
                FeatureState.Available, FeatureName.SetVolume
            )
        )
        await self.atv.audio.set_volume(20.0)
        await until(lambda: math.isclose(self.atv.audio.volume, 20.0))

        await self.atv.audio.volume_up()
        await until(lambda: self.atv.audio.volume == round(20.0 + VOLUME_STEP * 100.0))

        await self.atv.audio.volume_up()
        await until(
            lambda: self.atv.audio.volume == round(20.0 + 2 * VOLUME_STEP * 100.0)
        )

    async def test_audio_volume_up_increases_volume_relative(self):
        self.usecase.change_volume_control(
            available=True, support_absolute=True, support_relative=True
        )
        await self._test_audio_volume_up_increases_volume()

    async def test_audio_volume_up_increases_volume_absolute(self):
        self.usecase.change_volume_control(
            available=True, support_absolute=True, support_relative=False
        )
        await self._test_audio_volume_up_increases_volume()

    async def _test_audio_volume_down_decreases_volume(self):
        self.usecase.change_volume_control(available=True)

        await until(
            lambda: self.atv.features.in_state(
                FeatureState.Available, FeatureName.SetVolume
            )
        )
        await self.atv.audio.set_volume(20.0)
        await until(lambda: math.isclose(self.atv.audio.volume, 20.0))

        await self.atv.audio.volume_down()
        await until(lambda: self.atv.audio.volume == round(20 - VOLUME_STEP * 100.0))

        await self.atv.audio.volume_down()
        await until(
            lambda: self.atv.audio.volume == round(20 - 2 * VOLUME_STEP * 100.0)
        )

    async def test_audio_volume_down_decreases_volume_relative(self):
        self.usecase.change_volume_control(
            available=True, support_absolute=True, support_relative=True
        )
        await self._test_audio_volume_down_decreases_volume()

    async def test_audio_volume_down_decreases_volume_absolute(self):
        self.usecase.change_volume_control(
            available=True, support_absolute=True, support_relative=False
        )
        await self._test_audio_volume_down_decreases_volume()

    async def _test_audio_volume_up_above_max(self):
        await until(
            lambda: self.atv.features.in_state(
                FeatureState.Available, FeatureName.SetVolume
            )
        )
        await self.atv.audio.set_volume(100.0)
        await until(lambda: math.isclose(self.atv.audio.volume, 100.0))

        # Should not yield a timeout
        await self.atv.audio.volume_up()

    async def test_audio_volume_up_above_max_relative(self):
        self.usecase.change_volume_control(
            available=True, support_absolute=True, support_relative=True
        )
        await self._test_audio_volume_up_above_max()

    async def test_audio_volume_up_above_max_absolute(self):
        self.usecase.change_volume_control(
            available=True, support_absolute=True, support_relative=False
        )
        await self._test_audio_volume_up_above_max()

    async def _test_audio_volume_down_below_zero(self):
        await until(
            lambda: self.atv.features.in_state(
                FeatureState.Available, FeatureName.SetVolume
            )
        )
        await self.atv.audio.set_volume(0.0)
        await until(lambda: math.isclose(self.atv.audio.volume, 0.0))

        # Should not yield a timeout
        await self.atv.audio.volume_down()

    async def test_audio_volume_down_below_zero_relative(self):
        self.usecase.change_volume_control(
            available=True, support_absolute=True, support_relative=True
        )
        await self._test_audio_volume_down_below_zero()

    async def test_audio_volume_down_below_zero_absolute(self):
        self.usecase.change_volume_control(
            available=True, support_absolute=True, support_relative=False
        )
        await self._test_audio_volume_down_below_zero()

    async def test_volume_clustered_devices(self):
        cluster_id = "AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE"
        self.usecase.set_cluster_id(cluster_id)
        self.usecase.change_volume_control(available=True)

        await until(
            lambda: self.atv.features.in_state(
                FeatureState.Available, FeatureName.SetVolume
            )
        )

        # Manually set a new volume level
        await self.atv.audio.set_volume(20.0)
        await until(lambda: math.isclose(self.atv.audio.volume, 20.0))

        # Trigger volume change from device with wrong id
        self.usecase.set_volume(0.3, DEVICE_UID)
        await until(lambda: math.isclose(self.atv.audio.volume, 20.0))

        # Trigger volume change from device
        self.usecase.set_volume(0.3, cluster_id)
        await until(lambda: math.isclose(self.atv.audio.volume, 30.0))

    async def test_output_devices(self):
        assert self.atv.audio.output_devices == [
            OutputDevice("Fake MRP ATV", "E510C430-B01D-45DF-B558-6EA6F8251069")
        ]

    async def test_output_devices_change(self):
        await self.atv.audio.add_output_devices("AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE")
        await until(
            lambda: self.atv.audio.output_devices
            == [
                OutputDevice("Fake MRP ATV", "E510C430-B01D-45DF-B558-6EA6F8251069"),
                OutputDevice("Device AA", "AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE"),
            ]
        )

        await self.atv.audio.remove_output_devices(
            "E510C430-B01D-45DF-B558-6EA6F8251069"
        )
        await until(
            lambda: self.atv.audio.output_devices
            == [OutputDevice("Device AA", "AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE")]
        )

        await self.atv.audio.set_output_devices("E510C430-B01D-45DF-B558-6EA6F8251069")
        await until(
            lambda: self.atv.audio.output_devices
            == [OutputDevice("Fake MRP ATV", "E510C430-B01D-45DF-B558-6EA6F8251069")]
        )
