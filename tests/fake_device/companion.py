"""Fake Companion Apple TV for tests."""

import asyncio
from dataclasses import dataclass
from enum import IntFlag, auto
import logging
import plistlib
from typing import Any, Dict, List, Mapping, Optional, Set

from pyatv.const import KeyboardFocusState, TouchAction
from pyatv.protocols.companion import (
    HidCommand,
    MediaControlCommand,
    MediaControlFlags,
    keyed_archiver,
)
from pyatv.protocols.companion.api import SystemStatus
from pyatv.protocols.companion.connection import FrameType
from pyatv.protocols.companion.server_auth import CompanionServerAuth
from pyatv.support import chacha20, log_binary, opack

_LOGGER = logging.getLogger(__name__)

DEVICE_NAME = "Fake Companion ATV"
INITIAL_VOLUME = 10.0
INITIAL_DURATION = 10.0
VOLUME_STEP = 5.0
INITIAL_RTI_TEXT = "Fake Companion Keyboard Text"

COMPANION_AUTH_FRAMES = [
    FrameType.PS_Start,
    FrameType.PS_Next,
    FrameType.PV_Start,
    FrameType.PV_Next,
]

HID_BUTTON_MAP = {
    HidCommand.Up: "up",
    HidCommand.Down: "down",
    HidCommand.Left: "left",
    HidCommand.Right: "right",
    HidCommand.Select: "select",
    HidCommand.Menu: "menu",
    HidCommand.Home: "home",
    HidCommand.VolumeDown: "volume_down",
    HidCommand.VolumeUp: "volume_up",
    HidCommand.PlayPause: "play_pause",
    HidCommand.ChannelIncrement: "channel_up",
    HidCommand.ChannelDecrement: "channel_down",
    HidCommand.Screensaver: "screensaver",
}

MEDIA_CONTROL_MAP = {
    MediaControlCommand.Play: "play",
    MediaControlCommand.Pause: "pause",
    MediaControlCommand.NextTrack: "next",
    MediaControlCommand.PreviousTrack: "previous",
    MediaControlCommand.SetVolume: "set_volume",
    MediaControlCommand.SkipBy: "skip",
}


@dataclass
class HidEvent:
    press_mode: TouchAction
    x: int
    y: int
    ns: int


class CompanionServiceFlags(IntFlag):
    """Flags used to alter fake service behavior."""

    EMPTY = auto()
    """Empty service flag."""

    SYSTEM_STATUS_SUPPORTED = auto()
    """If system status is supported."""


class FakeCompanionState:
    def __init__(self):
        """State of a fake Companion device."""
        self.flags: CompanionServiceFlags = (
            CompanionServiceFlags.EMPTY | CompanionServiceFlags.SYSTEM_STATUS_SUPPORTED
        )
        self.clients: List[FakeCompanionService] = []
        self._system_status: SystemStatus = SystemStatus.Awake
        self.active_app: Optional[str] = None
        self.open_url: Optional[str] = None
        self.installed_apps: Dict[str, str] = {}
        self.active_account: Optional[str] = None
        self.available_accounts: Dict[str, str] = {}
        self.has_paired: bool = False
        self.powered_on: bool = True
        self.sid: int = 0
        self.service_type: Optional[str] = None
        self.latest_button: Optional[str] = None
        self.media_control_flags: int = MediaControlFlags.Volume
        self.interests: Set[str] = set()
        self.volume: float = INITIAL_VOLUME
        self.duration: float = INITIAL_DURATION
        self.rti_clients: List[FakeCompanionService] = []
        self._rti_focus_state: KeyboardFocusState = KeyboardFocusState.Focused
        self.rti_text: Optional[str] = INITIAL_RTI_TEXT
        self.rti_session_uuid: Optional[bytes] = None
        self.touch_event: HidEvent | None = None
        self.touch_width = 0
        self.touch_height = 0

    def is_supported(self, flag: CompanionServiceFlags) -> bool:
        """Return if a feature is supported."""
        return flag in self.flags

    def set_flag_state(self, flag: CompanionServiceFlags, enabled: bool) -> None:
        """Set if a feature is supported or not."""
        if enabled:
            self.flags |= flag
        else:
            self.flags &= ~flag

    @property
    def system_status(self) -> SystemStatus:
        return self._system_status

    @system_status.setter
    def system_status(self, value) -> None:
        self._system_status = value

        # Only send event updates if feature is supported
        if self.is_supported(CompanionServiceFlags.SYSTEM_STATUS_SUPPORTED):
            for client in self.clients:
                client.send_event(
                    "SystemStatus", 1234, {"state": self.system_status.value}
                )

    def _send_rti(self, identifier, content):
        for client in self.rti_clients:
            client.send_event(identifier, 1234, content)

    @property
    def rti_focus_state(self) -> KeyboardFocusState:
        return self._rti_focus_state

    @rti_focus_state.setter
    def rti_focus_state(self, value: KeyboardFocusState) -> None:
        if value == self._rti_focus_state:
            return
        self._rti_focus_state = value
        if value == KeyboardFocusState.Focused:
            self._send_rti("_tiStarted", self.rti_encoded_data)
        elif value == KeyboardFocusState.Unfocused:
            self._send_rti("_tiStopped", self.rti_encoded_data)

    @property
    def rti_encoded_data(self) -> Mapping[str, Any]:
        if self.rti_focus_state == KeyboardFocusState.Focused:
            return {
                "_tiD": plistlib.dumps(
                    {
                        "$top": {
                            "sessionUUID": plistlib.UID(1),
                            "documentState": plistlib.UID(2),
                        },
                        "$objects": (
                            [
                                "$null",
                                self.rti_session_uuid,
                                {
                                    "docSt": plistlib.UID(3),
                                },
                            ]
                            + [
                                {
                                    "contextBeforeInput": plistlib.UID(4),
                                },
                                self.rti_text,
                            ]
                            if self.rti_text is not None
                            else [{}]
                        ),
                    },
                    fmt=plistlib.PlistFormat.FMT_BINARY,
                    sort_keys=False,
                )
            }
        else:
            return {}

    @property
    def touch_event_state(self) -> HidEvent:
        return self.touch_event


class FakeCompanionServiceFactory:
    def __init__(self, state, app, loop):
        self.state = state
        self.loop = loop
        self.server = None

    async def start(self, start_web_server: bool):
        def _server_factory():
            try:
                return FakeCompanionService(self.state)
            except Exception:
                _LOGGER.exception("failed to create server")
                raise

        coro = self.loop.create_server(_server_factory, "0.0.0.0")
        self.server = await self.loop.create_task(coro)

        _LOGGER.info("Started Companion server at port %d", self.port)

    async def cleanup(self):
        if self.server:
            self.server.close()

    @property
    def port(self):
        return self.server.sockets[0].getsockname()[1]


class FakeCompanionService(CompanionServerAuth, asyncio.Protocol):
    """Implementation of a fake Companion Apple TV."""

    def __init__(self, state):
        super().__init__(DEVICE_NAME)
        self.loop = asyncio.get_event_loop()
        self.state = state
        self.buffer = b""
        self.chacha = None
        self.transport = None
        self._pressed_buttons: Set[HidCommand] = set()

    def connection_made(self, transport):
        _LOGGER.debug("Client connected")
        self.transport = transport
        self.state.clients.append(self)

    def connection_lost(self, exc):
        _LOGGER.debug("Client disconnected")
        self.transport = None
        self.state.clients.remove(self)

    def enable_encryption(self, output_key: bytes, input_key: bytes) -> None:
        """Enable encryption with specified keys."""
        self.chacha = chacha20.Chacha20Cipher(output_key, input_key, nonce_length=12)

    def has_paired(self):
        """Call when a client has paired."""
        self.state.has_paired = True

    def send_to_client(self, frame_type: FrameType, data: object) -> None:
        _LOGGER.debug("Send %s with data: %s", frame_type, data)

        data = opack.pack(data)

        payload_length = len(data) + (16 if self.chacha else 0)
        header = bytes([frame_type.value]) + payload_length.to_bytes(3, byteorder="big")

        if self.chacha:
            data = self.chacha.encrypt(data, aad=header)

        log_binary(_LOGGER, ">> Send", Header=header, Data=data)
        self.transport.write(header + data)

    def data_received(self, data):
        self.buffer += data

        while self.buffer:
            payload_length = 4 + int.from_bytes(self.buffer[1:4], byteorder="big")
            if len(self.buffer) < payload_length:
                _LOGGER.debug(
                    "Expect %d bytes, have %d bytes", payload_length, len(self.buffer)
                )
                break

            frame_type = FrameType(self.buffer[0])
            header = self.buffer[0:4]
            data = self.buffer[4:payload_length]
            self.buffer = self.buffer[payload_length:]

            if self.chacha:
                data = self.chacha.decrypt(data, aad=header)

            unpacked, _ = opack.unpack(data)

            try:
                if frame_type in COMPANION_AUTH_FRAMES:
                    self.handle_auth_frame(frame_type, unpacked)
                else:
                    if not self.chacha:
                        raise Exception("client has not authenticated")

                    _LOGGER.debug("Received OPACK: %s", unpacked)
                    handler_method_name = f"handle_{unpacked['_i'].lower()}"
                    if hasattr(self, handler_method_name):
                        getattr(self, handler_method_name)(unpacked)
                    else:
                        self.send_handler_not_supported(unpacked)

            except Exception:
                _LOGGER.exception("failed to handle incoming data")

    def send_response(self, request, content):
        self.send_to_client(
            FrameType.E_OPACK,
            {
                "_i": request["_i"],
                "_x": request["_x"],
                "_t": 3,
                "_c": content,
            },
        )

    def send_event(self, identifier, xid, content):
        self.send_to_client(
            FrameType.E_OPACK,
            {
                "_i": identifier,
                "_x": xid,
                "_t": 1,
                "_c": content,
            },
        )

    def send_error(
        self, request, message, /, code: int = 1337, domain: str = "RPErrorDomain"
    ):
        self.send_to_client(
            FrameType.E_OPACK,
            {
                "_i": request["_i"],
                "_x": request["_x"],
                "_t": 3,
                "_ec": code,
                "_ed": domain,
                "_em": message,
            },
        )

    def send_handler_not_supported(self, request):
        _LOGGER.warning("No handler for type %s", request["_i"])
        self.send_error(request, "No request handler", code=58822)

    def volume_changed(self, new_volume: float):
        self.state.volume = min(max(new_volume, 0.0), 100.0)
        _LOGGER.debug("Volume changed to %f", self.state.volume)

        self.send_event(
            "_iMC",
            1234,
            {"_mcF": self.state.media_control_flags | MediaControlFlags.Volume},
        )

    def handle__launchapp(self, message):
        bundle_id = message["_c"].get("_bundleID")
        url = message["_c"].get("_urlS")
        if bundle_id is not None:
            self.state.active_app = bundle_id
        elif url is not None:
            self.state.open_url = url
        self.send_response(message, {})

    def handle_fetchlaunchableapplicationsevent(self, message):
        self.send_response(message, self.state.installed_apps)

    def handle_switchuseraccountevent(self, message):
        payload = message["_c"]
        self.state.active_account = payload.get("SwitchAccountID")
        self.send_response(message, {})

    def handle_fetchuseraccountsevent(self, message):
        self.send_response(message, self.state.available_accounts)

    def handle__hidc(self, message):
        button_state = message["_c"]["_hBtS"]
        button_code = HidCommand(message["_c"]["_hidC"])

        if button_state == 1:
            _LOGGER.debug("Button %s pressed DOWN", button_code)
            self._pressed_buttons.add(button_code)
        elif button_state == 2 and button_code == HidCommand.Sleep:
            _LOGGER.debug("Putting device to sleep")
            self.state.powered_on = False
        elif button_state == 2 and button_code == HidCommand.Wake:
            _LOGGER.debug("Waking up device")
            self.state.powered_on = True
        elif button_code in HID_BUTTON_MAP:
            if button_code not in self._pressed_buttons:
                _LOGGER.warning("Button UP with no DOWN action for %s", button_code)
                self.send_error(message, f"Missing button DOWN for {button_code}")
                return

            _LOGGER.debug("Button pressed: %s", HID_BUTTON_MAP[button_code])
            self._pressed_buttons.remove(button_code)
            self.state.latest_button = HID_BUTTON_MAP[button_code]

            # Buttons that change volume
            if button_code == HidCommand.VolumeUp:
                self.volume_changed(self.state.volume + VOLUME_STEP)
            elif button_code == HidCommand.VolumeDown:
                self.volume_changed(self.state.volume - VOLUME_STEP)
        else:
            _LOGGER.warning("Unhandled command: %d %s", button_state, button_code)
            return  # Would be good to send error message here

        self.send_response(message, {})

    def handle__touchstart(self, message):
        width = message["_c"]["_width"]
        height = message["_c"]["_height"]
        _LOGGER.debug(
            "Touch start command received with touchpad width %s and height %s",
            width,
            height,
        )
        self.state.touch_width = width
        self.state.touch_height = height
        if (
            not width
            or width < 0
            or width > 1000
            or not height
            or height < 0
            or height > 1000
        ):
            self.send_error(message, "Invalid touchpad width or height")
        else:
            self.send_response(message, {})

    def handle__touchstop(self, message):
        _LOGGER.debug("Touch stop command received")
        self.send_response(message, {})

    def handle__hidt(self, message):
        press_mode: int = message["_c"]["_tPh"]
        ns = message["_c"]["_ns"]
        cx = message["_c"]["_cx"]
        cy = message["_c"]["_cy"]
        if press_mode == TouchAction.Press:
            _LOGGER.debug("Touch event press to (%s, %s) at time %s", cx, cy, ns)
        elif TouchAction.Hold:
            _LOGGER.debug("Touch event move to (%s, %s) at time %s", cx, cy, ns)
        elif press_mode == TouchAction.Release:
            _LOGGER.debug("Touch event release to (%s, %s) at time %s", cx, cy, ns)
        elif press_mode == TouchAction.Click:
            _LOGGER.debug("Touch event click to (%s, %s) at time %s", cx, cy, ns)
        else:
            _LOGGER.warning("Touch event mode not supported %s", press_mode)
        self.state.action = HidEvent(TouchAction(press_mode), cx, cy, ns)

    def handle__mcc(self, message):
        args = {}
        mcc = MediaControlCommand(message["_c"]["_mcc"])

        if mcc == MediaControlCommand.SetVolume:
            # Make sure we send response before triggering event with volume update
            self.loop.call_soon(self.volume_changed(message["_c"]["_vol"] * 100.0))
        elif mcc == MediaControlCommand.GetVolume:
            args["_vol"] = self.state.volume / 100.0
        elif mcc == MediaControlCommand.SkipBy:
            self.state.duration = max(0, self.state.duration + message["_c"]["_skpS"])
        elif mcc in MEDIA_CONTROL_MAP:
            _LOGGER.debug("Activated Media Control Command %s", mcc)
            self.state.latest_button = MEDIA_CONTROL_MAP[mcc]
        else:
            _LOGGER.warning("Unsupported Media Control Code: %s", mcc)
            return

        self.send_response(message, args)

    def handle__sessionstart(self, message):
        self.state.sid = message["_c"]["_sid"]
        self.state.service_type = message["_c"]["_srvT"]
        self.send_response(message, {"_sid": 5555})

    def handle__sessionstop(self, message):
        if message["_c"]["_sid"] == (5555 << 32 | self.state.sid):
            self.state.sid = 0
            self.send_response(message, {})
        else:
            self.send_error(message, "Invalid SID")

    def handle__systeminfo(self, message):
        self.send_response(message, {})

    def handle__interest(self, message):
        content = message["_c"]
        if "_regEvents" in content:
            self.state.interests.update(content["_regEvents"])
            if "_iMC" in self.state.interests:
                self.send_event(
                    "_iMC", message["_x"], {"_mcF": self.state.media_control_flags}
                )
        elif "_deregEvents" in content:
            for event in content["_deregEvents"]:
                if event in self.state.interests:
                    self.state.interests.remove(event)

    def handle__tistart(self, message):
        if message["_t"] != 2:
            return
        elif self.state.rti_text is None:
            self.send_response(message, {})
            self.state.rti_clients.append(self)
        elif self.state.rti_session_uuid is not None:
            _LOGGER.warning("RTI session already started")
        else:
            self.state.rti_session_uuid = b"0123456789abcdef"
            self.send_response(message, self.state.rti_encoded_data)
            self.state.rti_clients.append(self)

    def handle__tistop(self, message):
        if message["_t"] != 2:
            return
        elif self.state.rti_session_uuid is not None:
            self.state.rti_session_uuid = None
            self.send_response(message, {})
            self.state.rti_clients.remove(self)
        else:
            _LOGGER.warning("No RTI session")

    def handle__tic(self, message):
        if message["_t"] != 1:
            return

        content = message["_c"]["_tiD"]
        (
            session_uuid,
            text_to_assert,
            insertion_text,
        ) = keyed_archiver.read_archive_properties(
            content,
            ["textOperations", "targetSessionUUID", "NS.uuidbytes"],
            ["textOperations", "textToAssert"],
            ["textOperations", "keyboardOutput", "insertionText"],
        )

        if session_uuid != self.state.rti_session_uuid:
            return

        if text_to_assert == "":
            self.state.rti_text = ""

        if insertion_text is not None:
            self.state.rti_text += insertion_text

    def handle_fetchattentionstate(self, message):
        if self.state.is_supported(CompanionServiceFlags.SYSTEM_STATUS_SUPPORTED):
            _LOGGER.debug("Returning system status: %s", self.state.system_status)
            self.send_response(message, {"state": self.state.system_status.value})
        else:
            self.send_handler_not_supported(message)


class FakeCompanionUseCases:
    """Wrapper for altering behavior of a FakeCompanionService instance."""

    def __init__(self, state: FakeCompanionState):
        """Initialize a new FakeCompanionUseCases."""
        self.state = state

    def set_installed_apps(self, apps: Dict[str, str]):
        """Set which apps that are currently installed."""
        self.state.installed_apps = apps

    def set_available_accounts(self, accounts: Dict[str, str]):
        """Set which user accounts are available."""
        self.state.available_accounts = accounts

    def set_control_flags(self, flags: int) -> None:
        """Set media control flags."""
        self.state.media_control_flags = flags

    def set_rti_focus_state(self, state: KeyboardFocusState) -> None:
        self.state.rti_focus_state = state

    def set_rti_text(self, text: Optional[str]) -> None:
        self.state.rti_text = text

    def set_system_status(self, system_status: SystemStatus) -> None:
        """Set a specific system state."""
        self.state.system_status = system_status
