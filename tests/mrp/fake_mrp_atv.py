"""Fake MRP Apple TV for tests."""

import asyncio
import logging

from pyatv.mrp import (messages, protobuf, variant)
from tests.airplay.fake_airplay_device import (
    FakeAirPlayDevice, AirPlayUseCases)

_LOGGER = logging.getLogger(__name__)


class FakeAppleTV(FakeAirPlayDevice, asyncio.Protocol):
    """Implementation of a fake MRP Apple TV."""

    def __init__(self, testcase):
        super().__init__(testcase)
        self.buttons_press_count = 0
        self.last_button_pressed = None

        self.server = None
        self.buffer = b''
        self.transport = None
        self.mapping = {
            protobuf.DEVICE_INFO_MESSAGE: self.handle_device_info,
            protobuf.CRYPTO_PAIRING_MESSAGE: self.handle_crypto_pairing,
            }

    @asyncio.coroutine
    def start(self, loop):
        coro = loop.create_server(lambda: self, '127.0.0.1')
        self.server = yield from loop.create_task(coro)
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
