"""Fake MRP Apple TV for tests."""

import asyncio
import logging
import struct

from pyatv.mrp import (messages, protobuf, variant)
from pyatv.mrp.protobuf import CommandInfo_pb2 as cmd
from tests.airplay.fake_airplay_device import (
    FakeAirPlayDevice, AirPlayUseCases)

_LOGGER = logging.getLogger(__name__)

_KEY_LOOKUP = {
    # name: [usage_page, usage, button hold time (seconds)]
    'up': [1, 0x8C, 0],
    'down': [1, 0x8D, 0],
    'left': [1, 0x8B, 0],
    'right': [1, 0x8A, 0],
    'stop': [12, 0xB7, 0],
    'next': [12, 0xB5, 0],
    'previous': [12, 0xB6, 0],
    'select': [1, 0x89, 0],
    'menu': [1, 0x86, 0],
    'topmenu': [12, 0x60, 0],
    'home': [12, 0x40, 0],
    'home_hold': [12, 0x40, 1],
    'suspend': [1, 0x82, 0],
    'wakeup': [1, 0x83, 0],
    'volume_up': [12, 0xE9, 0],
    'volume_down': [12, 0xEA, 0],
}

_COMMAND_LOOKUP = {
    cmd.Play: 'play',
    cmd.Pause: 'pause',
    cmd.Stop: 'stop',
    cmd.NextTrack: 'nextitem',
    cmd.PreviousTrack: 'previtem',
}


def _convert_key_press(use_page, usage):
    for name, codes in _KEY_LOOKUP.items():
        if codes[0] == use_page and codes[1] == usage:
            return name
    raise Exception(
        'unsupported key: use_page={0}, usage={1}'.format(
            use_page, usage))


class FakeAppleTV(FakeAirPlayDevice, asyncio.Protocol):
    """Implementation of a fake MRP Apple TV."""

    def __init__(self, testcase, loop):
        super().__init__(testcase)
        self.loop = loop
        self.app.on_startup.append(self.start)
        self.outstanding_keypresses = set()  # Pressed but not released
        self.last_button_pressed = None
        self.connection_state = None

        self.server = None
        self.buffer = b''
        self.transport = None
        self.mapping = {
            protobuf.DEVICE_INFO_MESSAGE: self.handle_device_info,
            protobuf.CRYPTO_PAIRING_MESSAGE: self.handle_crypto_pairing,
            protobuf.SET_CONNECTION_STATE_MESSAGE:
                self.handle_set_connection_state,
            protobuf.CLIENT_UPDATES_CONFIG_MESSAGE:
                self.handle_client_updates_config_message,
            protobuf.GET_KEYBOARD_SESSION_MESSAGE:
                self.handle_get_keyboard_session_message,
            protobuf.SEND_HID_EVENT_MESSAGE:
                self.handle_send_hid_event_message,
            protobuf.SEND_COMMAND_MESSAGE:
                self.handle_send_command_message,
            }

    async def start(self, app):
        coro = self.loop.create_server(lambda: self, '127.0.0.1')
        self.server = await self.loop.create_task(coro)
        _LOGGER.info('Started MRP server at port %d', self.port)

    @property
    def port(self):
        return self.server.sockets[0].getsockname()[1]

    def connection_made(self, transport):
        self.transport = transport

    def _send(self, message):
        data = message.SerializeToString()
        length = variant.write_variant(len(data))
        self.transport.write(length + data)

    def data_received(self, data):
        self.buffer += data

        while self.buffer:
            length, raw = variant.read_variant(self.buffer)
            if len(raw) < length:
                return

            data = raw[:length]
            self.buffer = raw[length:]
            parsed = protobuf.ProtocolMessage()
            parsed.ParseFromString(data)
            _LOGGER.info('Incoming message: %s', parsed)

            try:
                def unhandled_message(message):
                    _LOGGER.warning('No message handler for %s', message)

                self.mapping.get(parsed.type, unhandled_message)(parsed)
            except Exception:
                _LOGGER.exception('Error while dispatching message')

    def handle_device_info(self, message):
        _LOGGER.debug('Received device info message')

        resp = messages.device_information('Fake MRP ATV', '1234')
        resp.identifier = message.identifier
        self._send(resp)

    def handle_crypto_pairing(self, message):
        _LOGGER.debug('Received crypto pairing message')

    def handle_set_connection_state(self, message):
        inner = message.inner()
        _LOGGER.debug('Changed connection state to %d', inner.state)
        self.connection_state = inner.state

    def handle_client_updates_config_message(self, message):
        _LOGGER.debug('Update client config')

    def handle_get_keyboard_session_message(self, message):
        _LOGGER.debug('Get keyboard session')

        # This message has a lot more fields, but pyatv currently
        # not use them so ignore for now
        resp = messages.create(protobuf.KEYBOARD_MESSAGE)
        resp.identifier = message.identifier
        self._send(resp)

    def handle_send_hid_event_message(self, message):
        _LOGGER.debug('Got HID event message')

        hid_data = message.inner().hidEventData

        # These corresponds to the bytes mapping to pressed key (see
        # send_hid_event in pyatv/mrp/messages.py)
        start = hid_data[43:49]
        use_page, usage, down_press = struct.unpack('>HHH', start)

        if down_press == 1:
            self.outstanding_keypresses.add((use_page, usage))
        elif down_press == 0:
            if (use_page, usage) in self.outstanding_keypresses:
                self.last_button_pressed = _convert_key_press(use_page, usage)
                self.outstanding_keypresses.remove((use_page, usage))
                _LOGGER.debug('Pressed button: %s', self.last_button_pressed)
            else:
                _LOGGER.error('Missing key down for %d,%d', use_page, usage)
        else:
            _LOGGER.error('Invalid key press state: %d', down_press)

    def handle_send_command_message(self, message):
        _LOGGER.debug('Got command message')

        button = _COMMAND_LOOKUP.get(message.inner().command)
        if button:
            self.last_button_pressed = button
            _LOGGER.debug('Pressed button: %s', self.last_button_pressed)
        else:
            _LOGGER.warning(
                'Unhandled button press: %s', message.inner().command)


class AppleTVUseCases(AirPlayUseCases):
    """Wrapper for altering behavior of a FakeMrpAppleTV instance."""

    def __init__(self, fake_apple_tv):
        """Initialize a new AppleTVUseCases."""
        self.device = fake_apple_tv

    def change_artwork(self, artwork):
        """Call this method to change artwork response."""
        pass

    def nothing_playing(self):
        """Call this method to put device in idle state."""
        pass

    def example_video(self, **kwargs):
        """Play some example video."""
        pass

    def video_playing(self, paused, title, total_time, position, **kwargs):
        """Call this method to change what is currently plaing to video."""
        pass

    def music_playing(self, paused, artist, album, title, genre,
                      total_time, position):
        """Call this method to change what is currently plaing to music."""
        pass

    def media_is_loading(self):
        """Call this method to put device in a loading state."""
        pass
