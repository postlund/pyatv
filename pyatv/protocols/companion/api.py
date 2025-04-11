"""High level implementation of Companion API."""

import asyncio
from enum import Enum
import logging
from random import randint
import time
from typing import Any, Dict, List, Mapping, Optional, cast

from pyatv import exceptions
from pyatv.auth.hap_pairing import parse_credentials
from pyatv.auth.hap_srp import SRPAuthHandler
from pyatv.const import InputAction, TouchAction
from pyatv.core import Core
from pyatv.core.protocol import MessageDispatcher
from pyatv.protocols.companion import keyed_archiver
from pyatv.protocols.companion.connection import CompanionConnection, FrameType
from pyatv.protocols.companion.plist_payloads import (
    get_rti_clear_text_payload,
    get_rti_input_text_payload,
)
from pyatv.protocols.companion.protocol import (
    CompanionProtocol,
    CompanionProtocolListener,
    MessageType,
)
from pyatv.support.url import is_url_or_scheme

_LOGGER = logging.getLogger(__name__)


# pylint: disable=invalid-name


class HidCommand(Enum):
    """HID command constants."""

    Up = 1
    Down = 2
    Left = 3
    Right = 4
    Menu = 5
    Select = 6
    Home = 7
    VolumeUp = 8
    VolumeDown = 9
    Siri = 10
    Screensaver = 11
    Sleep = 12
    Wake = 13
    PlayPause = 14
    ChannelIncrement = 15
    ChannelDecrement = 16
    Guide = 17
    PageUp = 18
    PageDown = 19


class MediaControlCommand(Enum):
    """Media Control command constants."""

    Play = 1
    Pause = 2
    NextTrack = 3
    PreviousTrack = 4
    GetVolume = 5
    SetVolume = 6
    SkipBy = 7
    FastForwardBegin = 8
    FastForwardEnd = 9
    RewindBegin = 10
    RewindEnd = 11
    GetCaptionSettings = 12
    SetCaptionSettings = 13


class SystemStatus(Enum):
    """Current system state."""

    Unknown = 0x00  # NB: Not a valid protocol entry (only used here)

    Asleep = 0x01
    Screensaver = 0x02
    Awake = 0x03
    Idle = 0x04  # NB: Not verified


TOUCHPAD_WIDTH = 1000.0  # Touchpad width
TOUCHPAD_HEIGHT = 1000.0  # Touchpad height
TOUCHPAD_DELAY_MS = 16  # Delay between touch events in ms
# pylint: enable=invalid-name


class CompanionAPI(
    MessageDispatcher[str, Mapping[str, Any]], CompanionProtocolListener
):
    """Implementation of Companion API."""

    def __init__(self, core: Core):
        """Initialize a new CompanionAPI instance."""
        super().__init__()
        self.core = core
        self._connection: Optional[CompanionConnection] = None
        self._protocol: Optional[CompanionProtocol] = None
        self._subscribed_events: List[str] = []
        self.sid: int = 0
        self._base_timestamp = time.time_ns()

    async def disconnect(self):
        """Disconnect from companion device."""
        if self._protocol is None:
            return

        try:
            for event in self._subscribed_events:
                await self.unsubscribe_event(event)

            # Sometimes unsubscribe fails for an unknown reason, but we are no
            # going to bother with that and just swallow the error.
            await self._session_stop()

            await self._touch_stop()
            await self._text_input_stop()
        except Exception as ex:
            _LOGGER.debug("Ignoring error during disconnect: %s", ex)
        finally:
            self._protocol.stop()
            self._protocol = None

    def event_received(self, event_name: str, data: Dict[str, Any]) -> None:
        """Event was received."""
        _LOGGER.debug("Got event %s from device: %s", event_name, data)
        self.dispatch(event_name, data)

    async def connect(self):
        """Connect to remote host."""
        if self._protocol:
            return

        _LOGGER.debug("Connect to Companion from API")
        self._connection = CompanionConnection(
            self.core.loop,
            str(self.core.config.address),
            self.core.service.port,
            self.core.device_listener,
        )
        self._protocol = CompanionProtocol(
            self._connection, SRPAuthHandler(), self.core.service
        )
        self._protocol.listener = self
        await self._protocol.start()

        await self.system_info()
        await self._touch_start()
        await self._session_start()
        await self._text_input_start()

        await self.subscribe_event("_iMC")

    async def _send_command(
        self,
        identifier: str,
        content: Dict[str, object],
        message_type: MessageType = MessageType.Request,
    ) -> Mapping[str, Any]:
        """Send a command to the device and return response."""
        await self.connect()
        if self._protocol is None:
            raise RuntimeError("not connected to companion")

        try:
            resp = await self._protocol.exchange_opack(
                FrameType.E_OPACK,
                {
                    "_i": identifier,
                    "_t": message_type.value,
                    "_c": content,
                },
            )
        except exceptions.ProtocolError:
            raise
        except Exception as ex:
            raise exceptions.ProtocolError(f"Command {identifier} failed") from ex
        return resp

    async def system_info(self):
        """Send system information to device."""
        _LOGGER.debug("Sending system information")
        creds = parse_credentials(self.core.service.credentials)
        info = self.core.settings.info

        # Bunch of semi-random values here...
        await self._send_command(
            "_systemInfo",
            {
                "_bf": 0,
                "_cf": 512,
                "_clFl": 128,
                "_i": info.rp_id,
                "_idsID": creds.client_id,
                # Not really device id here, but better then anything...
                "_pubID": info.device_id,
                "_sf": 256,  # Status flags?
                "_sv": "170.18",  # Software Version (I guess?)
                "model": info.model,
                "name": info.name,
            },
        )

    async def _session_start(self) -> None:
        local_sid = randint(0, 2**32 - 1)
        resp = await self._send_command(
            "_sessionStart", {"_srvT": "com.apple.tvremoteservices", "_sid": local_sid}
        )

        content = resp.get("_c")
        if content is None:
            raise exceptions.ProtocolError("missing content")

        remote_sid = cast(Mapping[str, Any], resp["_c"])["_sid"]
        self.sid = (remote_sid << 32) | local_sid
        _LOGGER.debug("Started session with SID 0x%X", self.sid)

    async def _session_stop(self) -> None:
        await self._send_command(
            "_sessionStop", {"_srvT": "com.apple.tvremoteservices", "_sid": self.sid}
        )
        _LOGGER.debug("Stopped session with SID 0x%X", self.sid)

    async def _send_event(self, identifier: str, content: Mapping[str, Any]) -> None:
        """Subscribe to updates to an event."""
        await self.connect()
        if self._protocol is None:
            raise RuntimeError("not connected to companion")

        try:
            self._protocol.send_opack(
                FrameType.E_OPACK,
                {
                    "_i": identifier,
                    "_t": MessageType.Event.value,
                    "_c": content,
                },
            )
        except exceptions.ProtocolError:
            raise
        except Exception as ex:
            raise exceptions.ProtocolError("Send event failed") from ex

    async def subscribe_event(self, event: str) -> None:
        """Subscribe to updates to an event."""
        if event not in self._subscribed_events:
            await self._send_event("_interest", {"_regEvents": [event]})
            self._subscribed_events.append(event)

    async def unsubscribe_event(self, event: str) -> None:
        """Subscribe to updates to an event."""
        if event in self._subscribed_events:
            await self._send_event("_interest", {"_deregEvents": [event]})
            self._subscribed_events.remove(event)

    async def launch_app(self, bundle_identifier_or_url: str) -> None:
        """Launch an app on the remote device."""
        launch_command_key = (
            "_urlS" if is_url_or_scheme(bundle_identifier_or_url) else "_bundleID"
        )
        await self._send_command(
            "_launchApp",
            {
                launch_command_key: bundle_identifier_or_url,
            },
        )

    async def app_list(self) -> Mapping[str, Any]:
        """Return list of launchable apps on remote device."""
        return await self._send_command("FetchLaunchableApplicationsEvent", {})

    async def switch_account(self, account_id: str) -> None:
        """Switch user account on the remote device."""
        await self._send_command(
            "SwitchUserAccountEvent", {"SwitchAccountID": account_id}
        )

    async def account_list(self) -> Mapping[str, Any]:
        """Return list of user accounts on remote device."""
        return await self._send_command("FetchUserAccountsEvent", {})

    async def hid_command(self, down: bool, command: HidCommand) -> None:
        """Send a HID command."""
        await self._send_command(
            "_hidC", {"_hBtS": 1 if down else 2, "_hidC": command.value}
        )

    async def hid_event(self, x: int, y: int, mode: TouchAction) -> None:
        """Send a HID command."""
        x = max(x, 0)
        y = max(y, 0)
        x = min(x, int(TOUCHPAD_WIDTH))
        y = min(y, int(TOUCHPAD_HEIGHT))
        await self._send_event(
            identifier="_hidT",
            content={
                "_ns": (time.time_ns() - self._base_timestamp),
                "_tFg": 1,
                "_cx": x,
                "_tPh": mode.value,
                "_cy": y,
            },
        )

    async def swipe(
        self, start_x: int, start_y: int, end_x: int, end_y: int, duration_ms: int
    ):
        """Generate a swipe gesture.

         From start to end x,y coordinates (in range [0,1000])
         in a given time (in milliseconds).

        :param start_x: Start x coordinate
        :param start_y: Start y coordinate
        :param end_x: End x coordinate
        :param end_y: Endi x coordinate
        :param duration_ms: Time in milliseconds to reach the end coordinates
        """
        end_time = time.time_ns() + duration_ms * 1000000
        x: float = float(start_x)
        y: float = float(start_y)
        await self.hid_event(int(x), int(y), TouchAction.Press)
        sleep_time = float(TOUCHPAD_DELAY_MS / 1000)
        current_time = time.time_ns()
        while current_time < end_time:
            x = x + float(end_x - x) * TOUCHPAD_DELAY_MS * 1000000 / (
                end_time - current_time
            )
            y = y + float(end_y - y) * TOUCHPAD_DELAY_MS * 1000000 / (
                end_time - current_time
            )
            x = max(x, 0)
            y = max(y, 0)
            x = min(x, TOUCHPAD_WIDTH)
            y = min(y, TOUCHPAD_HEIGHT)
            await self.hid_event(int(x), int(y), TouchAction.Hold)
            await asyncio.sleep(sleep_time)
            current_time = time.time_ns()
        await self.hid_event(end_x, end_y, TouchAction.Release)

    async def action(self, x: int, y: int, mode: TouchAction):
        """Generate a touch event to x,y coordinates (in range [0,1000]).

        :param x: x coordinate
        :param y: y coordinate
        :param mode: touch mode (1: press, 3: hold, 4: release)
        """
        await self.hid_event(x, y, mode)

    async def click(self, action: InputAction):
        """Send a touch click.

        :param action: action mode single tap (0), double tap (1), or hold (2)
        """
        if action in [InputAction.SingleTap, InputAction.DoubleTap]:
            count = 1 if action == InputAction.SingleTap else 2
            for _i in range(count):
                await self._send_command("_hidC", {"_hBtS": 1, "_hidC": 6})
                await asyncio.sleep(0.02)
                await self._send_command("_hidC", {"_hBtS": 2, "_hidC": 6})
                await self.hid_event(
                    int(TOUCHPAD_WIDTH), int(TOUCHPAD_HEIGHT), TouchAction.Click
                )
        else:  # Hold
            await self._send_command("_hidC", {"_hBtS": 1, "_hidC": 6})
            await asyncio.sleep(1)
            await self._send_command("_hidC", {"_hBtS": 2, "_hidC": 6})
            await self.hid_event(
                int(TOUCHPAD_WIDTH), int(TOUCHPAD_HEIGHT), TouchAction.Click
            )

    async def mediacontrol_command(
        self, command: MediaControlCommand, args: Optional[Mapping[str, Any]] = None
    ) -> Mapping[str, Any]:
        """Send a HID command."""
        return await self._send_command("_mcc", {"_mcc": command.value, **(args or {})})

    async def _text_input_start(self) -> Mapping[str, Any]:
        response = await self._send_command("_tiStart", {})
        await asyncio.gather(*self.dispatch("_tiStart", response.get("_c", {})))
        return response

    async def _text_input_stop(self) -> None:
        await self._send_command("_tiStop", {})

    async def text_input_command(
        self,
        text: str,
        clear_previous_input: bool = False,
    ) -> Optional[str]:
        """Send a text input command."""
        # restart the text input session so that we have up-to-date data
        await self._text_input_stop()
        response = await self._text_input_start()
        ti_data = response.get("_c", {}).get("_tiD")

        if ti_data is None:
            return None

        session_uuid, current_text = keyed_archiver.read_archive_properties(
            ti_data,
            ["sessionUUID"],
            ["documentState", "docSt", "contextBeforeInput"],
        )
        session_uuid = cast(bytes, session_uuid)
        if current_text is None:
            current_text = ""

        if clear_previous_input:
            await self._send_event(
                "_tiC",
                {
                    "_tiV": 1,
                    "_tiD": get_rti_clear_text_payload(session_uuid),
                },
            )
            current_text = ""

        if text:
            await self._send_event(
                "_tiC",
                {
                    "_tiV": 1,
                    "_tiD": get_rti_input_text_payload(session_uuid, text),
                },
            )
            current_text += text

        return current_text

    async def fetch_attention_state(self) -> SystemStatus:
        """Fetch attention state from device (system status)."""
        resp = await self._send_command("FetchAttentionState", {})
        content = resp.get("_c")

        if content is None:
            raise exceptions.ProtocolError("missing content")

        return SystemStatus(content["state"])

    async def _touch_start(self) -> Mapping[str, Any]:
        """Subscribe to touch gestures."""
        self._base_timestamp = time.time_ns()
        response = await self._send_command(
            "_touchStart",
            {"_height": TOUCHPAD_HEIGHT, "_tFl": 0, "_width": TOUCHPAD_WIDTH},
        )
        return response

    async def _touch_stop(self) -> None:
        """Unsubscribe touch gestures."""
        await self._send_command("_touchStop", {"_i": 1})
