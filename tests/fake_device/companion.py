"""Fake Companion Apple TV for tests."""

import asyncio
import logging
from typing import Dict, Optional, Set

from pyatv.protocols.companion import HidCommand, opack
from pyatv.protocols.companion.connection import FrameType
from pyatv.protocols.companion.server_auth import CompanionServerAuth
from pyatv.support import chacha20, log_binary

_LOGGER = logging.getLogger(__name__)

DEVICE_NAME = "Fake Companion ATV"

COMPANION_AUTH_FRAMES = [
    FrameType.PS_Start,
    FrameType.PS_Next,
    FrameType.PV_Start,
    FrameType.PV_Next,
]

BUTTON_MAP = {
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
}


class FakeCompanionState:
    def __init__(self):
        """State of a fake Companion device."""
        self.active_app: Optional[str] = None
        self.installed_apps: Dict[str, str] = {}
        self.has_paired: bool = False
        self.powered_on: bool = True
        self.sid: int = 0
        self.service_type: Optional[str] = None
        self.latest_button: Optional[str] = None
        self.media_control_flags: int = 0
        self.interests: Set[str] = set()


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
        self.state = state
        self.buffer = b""
        self.chacha = None
        self.transport = None

    def connection_made(self, transport):
        _LOGGER.debug("Client connected")
        self.transport = transport

    def connection_lost(self, exc):
        _LOGGER.debug("Client disconnected")
        self.transport = None

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
                        _LOGGER.warning("No handler for type %s", unpacked["_i"])

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

    def send_error(self, request, message):
        self.send_to_client(
            FrameType.E_OPACK,
            {
                "_i": request["_i"],
                "_x": request["_x"],
                "_t": 3,
                "_ec": 1337,
                "_ed": "RPErrorDomain",
                "_em": message,
            },
        )

    def handle__launchapp(self, message):
        self.state.active_app = message["_c"]["_bundleID"]
        self.send_response(message, {})

    def handle_fetchlaunchableapplicationsevent(self, message):
        self.send_response(message, self.state.installed_apps)

    def handle__hidc(self, message):
        button_state = message["_c"]["_hBtS"]
        button_code = HidCommand(message["_c"]["_hidC"])

        if button_state == 2 and button_code == HidCommand.Sleep:
            _LOGGER.debug("Putting device to sleep")
            self.state.powered_on = False
        elif button_state == 2 and button_code == HidCommand.Wake:
            _LOGGER.debug("Waking up device")
            self.state.powered_on = True
        elif button_state == 2 and button_code in BUTTON_MAP:
            _LOGGER.debug("Button pressed: %s", BUTTON_MAP[button_code])
            self.state.latest_button = BUTTON_MAP[button_code]
        else:
            _LOGGER.warning("Unhandled command: %d %s", button_state, button_code)
            return  # Would be good to send error message here

        self.send_response(message, {})

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


class FakeCompanionUseCases:
    """Wrapper for altering behavior of a FakeCompanionService instance."""

    def __init__(self, state):
        """Initialize a new FakeCompanionUseCases."""
        self.state = state

    def set_installed_apps(self, apps: Dict[str, str]):
        """Set which apps that are currently installed."""
        self.state.installed_apps = apps

    def set_control_flags(self, flags: int) -> None:
        """Set media control flags."""
        self.state.media_control_flags = flags
