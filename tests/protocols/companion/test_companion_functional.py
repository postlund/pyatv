"""Functional tests using the API with a fake Apple TV."""

import asyncio
import logging
import math

from deepdiff import DeepDiff
import pytest

import pyatv
from pyatv import exceptions
from pyatv.conf import AppleTV, ManualService
from pyatv.const import Protocol
from pyatv.interface import App, FeatureName, FeatureState

from tests.fake_device import FakeAppleTV
from tests.fake_device.companion import INITIAL_VOLUME, VOLUME_STEP
from tests.utils import until

_LOGGER = logging.getLogger(__name__)

TEST_APP: str = "com.test.Test"
TEST_APP_NAME: str = "Test"
TEST_APP2: str = "com.test.Test2"
TEST_APP_NAME2: str = "Test2"

MEDIA_CONTROL_FEATURES = [
    FeatureName.Play,
    FeatureName.Pause,
    FeatureName.Next,
    FeatureName.Previous,
    FeatureName.SkipForward,
    FeatureName.SkipBackward,
    FeatureName.Volume,
    FeatureName.SetVolume,
]

pytestmark = pytest.mark.asyncio


async def test_connect_only_companion(event_loop):
    service = ManualService(None, Protocol.Companion, 0, {})  # connect never happens
    conf = AppleTV("127.0.0.1", "Apple TV")
    conf.add_service(service)

    with pytest.raises(exceptions.DeviceIdMissingError):
        await pyatv.connect(conf, loop=event_loop)


async def test_subscribe_unsubscribe_media_control(companion_client, companion_state):
    await until(lambda: "_iMC" in companion_state.interests)

    await asyncio.gather(*companion_client.close())

    await until(lambda: "_iMC" not in companion_state.interests)


async def test_launch_app(companion_client, companion_state):
    await companion_client.apps.launch_app(TEST_APP)
    await until(lambda: companion_state.active_app == TEST_APP)


async def test_app_list(companion_client, companion_usecase):
    companion_usecase.set_installed_apps(
        {
            TEST_APP: TEST_APP_NAME,
            TEST_APP2: TEST_APP_NAME2,
        }
    )

    apps = await companion_client.apps.app_list()

    expected_apps = [App(TEST_APP_NAME, TEST_APP), App(TEST_APP_NAME2, TEST_APP2)]
    assert not DeepDiff(expected_apps, apps)


async def test_app_features(companion_client):
    assert (
        companion_client.features.get_feature(FeatureName.LaunchApp).state
        == FeatureState.Available
    )
    assert (
        companion_client.features.get_feature(FeatureName.AppList).state
        == FeatureState.Available
    )


@pytest.mark.parametrize(
    "features,expected_state",
    [
        (0x0000, FeatureState.Unavailable),
        (0xFFFF, FeatureState.Available),
    ],
)
async def test_media_control_features(
    companion_conf, event_loop, companion_usecase, features, expected_state
):
    companion_usecase.set_control_flags(features)

    atv = await pyatv.connect(companion_conf, loop=event_loop)

    for feature in MEDIA_CONTROL_FEATURES:
        await until(lambda: atv.features.get_feature(feature).state == expected_state)

    await asyncio.gather(*atv.close())


async def test_power_functions(companion_client, companion_state):
    assert companion_state.powered_on

    await companion_client.power.turn_off()
    assert not companion_state.powered_on

    await companion_client.power.turn_on()
    assert companion_state.powered_on


async def test_session_start_and_stop(companion_client, companion_state):
    assert companion_state.sid != 0
    assert companion_state.service_type == "com.apple.tvremoteservices"

    await asyncio.gather(*companion_client.close())

    assert companion_state.sid == 0


@pytest.mark.parametrize(
    "button",
    [
        # HID
        "up",
        "down",
        "left",
        "right",
        "select",
        "menu",
        "home",
        "volume_down",
        "volume_up",
        "play_pause",
        # Media Control
        "play",
        "pause",
        "next",
        "previous",
    ],
)
async def test_remote_control_buttons(companion_client, companion_state, button):
    await getattr(companion_client.remote_control, button)()
    assert companion_state.latest_button == button


async def test_audio_set_volume(companion_client, companion_state, companion_usecase):
    await until(lambda: companion_client.audio.volume, INITIAL_VOLUME)

    await companion_client.audio.set_volume(INITIAL_VOLUME + 1.0)
    assert math.isclose(companion_client.audio.volume, INITIAL_VOLUME + 1.0)
    await until(lambda: math.isclose(companion_state.volume, INITIAL_VOLUME + 1.0))


async def test_audio_volume_up(companion_client, companion_state):
    await until(lambda: companion_client.audio.volume, INITIAL_VOLUME)

    await companion_client.audio.volume_up()
    assert companion_client.audio.volume == INITIAL_VOLUME + VOLUME_STEP
    assert companion_state.latest_button == "volume_up"


async def test_audio_volume_down(companion_client, companion_state):
    await until(lambda: companion_client.audio.volume, INITIAL_VOLUME)

    await companion_client.audio.volume_down()
    assert companion_client.audio.volume == INITIAL_VOLUME - VOLUME_STEP
    assert companion_state.latest_button == "volume_down"
