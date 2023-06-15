"""Functional tests using the API with a fake Apple TV."""

import asyncio
import math

from deepdiff import DeepDiff
import pytest

import pyatv
from pyatv import exceptions
from pyatv.conf import AppleTV, ManualService
from pyatv.const import KeyboardFocusState, PowerState, Protocol
from pyatv.interface import App, FeatureName, FeatureState, UserAccount
from pyatv.protocols.companion.api import SystemStatus

from tests.fake_device.companion import (
    INITIAL_RTI_TEXT,
    INITIAL_VOLUME,
    VOLUME_STEP,
    CompanionServiceFlags,
)
from tests.shared_helpers import SavingPowerListener
from tests.utils import until

TEST_APP: str = "com.test.Test"
TEST_APP_NAME: str = "Test"
TEST_APP_URL: str = "com.test.Test://test/url?param0=value0"
TEST_APP2: str = "com.test.Test2"
TEST_APP_NAME2: str = "Test2"
TEST_ACCOUNT: str = "AAAAAAAA-AAAA-AAAA-AAAA-AAAAAAAAAAAA"
TEST_ACCOUNT_NAME: str = "Alice"
TEST_ACCOUNT2: str = "BBBBBBBB-BBBB-BBBB-BBBB-BBBBBBBBBBBB"
TEST_ACCOUNT_NAME2: str = "Bob"

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

ALWAYS_PRESENT_FEATURES = [
    FeatureName.TurnOn,
    FeatureName.TurnOff,
    FeatureName.Screensaver,
    FeatureName.AccountList,
    FeatureName.SwitchAccount,
    FeatureName.TextFocusState,
    FeatureName.TextGet,
    FeatureName.TextClear,
    FeatureName.TextAppend,
    FeatureName.TextSet,
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


async def test_launch_app_with_url(companion_client, companion_state):
    await companion_client.apps.launch_app(TEST_APP_URL)
    await until(lambda: companion_state.open_url == TEST_APP_URL)


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


async def test_switch_account(companion_client, companion_state):
    await companion_client.user_accounts.switch_account(TEST_ACCOUNT)
    await until(lambda: companion_state.active_account == TEST_ACCOUNT)


async def test_account_list(companion_client, companion_usecase):
    companion_usecase.set_available_accounts(
        {
            TEST_ACCOUNT: TEST_ACCOUNT_NAME,
            TEST_ACCOUNT2: TEST_ACCOUNT_NAME2,
        }
    )

    accounts = await companion_client.user_accounts.account_list()

    expected_apps = [
        UserAccount(TEST_ACCOUNT_NAME, TEST_ACCOUNT),
        UserAccount(TEST_ACCOUNT_NAME2, TEST_ACCOUNT2),
    ]
    assert not DeepDiff(expected_apps, accounts)


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


async def test_always_present_features(companion_conf, event_loop):
    atv = await pyatv.connect(companion_conf, loop=event_loop)

    for feature in ALWAYS_PRESENT_FEATURES:
        assert atv.features.get_feature(feature).state == FeatureState.Available

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
        "channel_up",
        "channel_down",
        # Media Control
        "play",
        "pause",
        "next",
        "previous",
        # Others
        "screensaver",
    ],
)
async def test_remote_control_buttons(companion_client, companion_state, button):
    await getattr(companion_client.remote_control, button)()
    assert companion_state.latest_button == button


async def test_audio_set_volume(companion_client, companion_state, companion_usecase):
    await until(lambda: companion_client.audio.volume, INITIAL_VOLUME)

    await companion_client.audio.set_volume(INITIAL_VOLUME + 1.0)
    await until(
        lambda: math.isclose(companion_client.audio.volume, INITIAL_VOLUME + 1.0)
    )
    assert math.isclose(companion_state.volume, INITIAL_VOLUME + 1.0)


async def test_audio_volume_up(companion_client, companion_state):
    await until(lambda: companion_client.audio.volume, INITIAL_VOLUME)

    await companion_client.audio.volume_up()
    await until(lambda: companion_client.audio.volume == INITIAL_VOLUME + VOLUME_STEP)
    assert companion_state.latest_button == "volume_up"


async def test_audio_volume_down(companion_client, companion_state):
    await until(lambda: companion_client.audio.volume, INITIAL_VOLUME)

    await companion_client.audio.volume_down()
    await until(lambda: companion_client.audio.volume == INITIAL_VOLUME - VOLUME_STEP)
    assert companion_state.latest_button == "volume_down"


async def test_text_input_text_focus_state(companion_client, companion_usecase):
    state = companion_client.keyboard.text_focus_state
    assert state == KeyboardFocusState.Focused

    companion_usecase.set_rti_focus_state(KeyboardFocusState.Unfocused)
    await until(
        lambda: companion_client.keyboard.text_focus_state
        == KeyboardFocusState.Unfocused
    )

    companion_usecase.set_rti_focus_state(KeyboardFocusState.Focused)
    await until(
        lambda: companion_client.keyboard.text_focus_state == KeyboardFocusState.Focused
    )


async def test_text_input_text_get(companion_client, companion_usecase):
    text = await companion_client.keyboard.text_get()
    assert text == INITIAL_RTI_TEXT

    companion_usecase.set_rti_text("test")
    text = await companion_client.keyboard.text_get()
    assert text == "test"


async def test_text_input_text_get_when_no_keyboard(
    companion_client, companion_usecase
):
    companion_usecase.set_rti_focus_state(KeyboardFocusState.Unfocused)
    text = await companion_client.keyboard.text_get()
    assert text is None


async def test_text_input_text_clear(companion_client, companion_state):
    await companion_client.keyboard.text_clear()
    await until(lambda: companion_state.rti_text == "")


async def test_text_input_text_append(companion_client, companion_state):
    await companion_client.keyboard.text_append("test")
    await until(lambda: companion_state.rti_text == INITIAL_RTI_TEXT + "test")


async def test_text_input_text_set(companion_client, companion_state):
    await companion_client.keyboard.text_set("test")
    await until(lambda: companion_state.rti_text == "test")


async def test_power_state_changes(
    companion_client, companion_state, companion_usecase
):
    listener = SavingPowerListener()
    companion_client.power.listener = listener

    # Fake device default state should be "on"
    await until(lambda: companion_client.power.power_state == PowerState.On)

    companion_usecase.set_system_status(SystemStatus.Asleep)
    await until(lambda: listener.last_update == PowerState.Off)

    companion_usecase.set_system_status(SystemStatus.Screensaver)
    await until(lambda: listener.last_update == PowerState.On)

    companion_usecase.set_system_status(SystemStatus.Asleep)
    await until(lambda: listener.last_update == PowerState.Off)

    companion_usecase.set_system_status(SystemStatus.Awake)
    await until(lambda: listener.last_update == PowerState.On)


@pytest.mark.parametrize(
    "system_status_supported, expected_feature_state, expecter_power_state",
    [
        (True, FeatureState.Available, PowerState.On),
        (False, FeatureState.Unsupported, PowerState.Unknown),
    ],
)
async def test_power_state_availability(
    event_loop,
    companion_conf,
    companion_state,
    system_status_supported,
    expected_feature_state,
    expecter_power_state,
):
    companion_state.set_flag_state(
        CompanionServiceFlags.SYSTEM_STATUS_SUPPORTED, system_status_supported
    )

    atv = await pyatv.connect(companion_conf, loop=event_loop)

    await until(
        lambda: atv.features.in_state(expected_feature_state, FeatureName.PowerState)
    )

    assert atv.power.power_state == expecter_power_state

    await asyncio.gather(*atv.close())
