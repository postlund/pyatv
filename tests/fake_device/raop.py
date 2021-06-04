"""Fake RAOP device for tests."""
import asyncio
import logging
from typing import Optional, cast

from pyatv.support.http import (
    BasicHttpServer,
    HttpRequest,
    HttpResponse,
    HttpSimpleRouter,
    http_server,
)

_LOGGER = logging.getLogger(__name__)


class AudioReceiver(asyncio.Protocol):
    """Protocol used to receive audio packets."""

    def __init__(self):
        """Initialize a new AudioReceiver instance."""
        self.transport = None

    def close(self):
        """Close audio receiver."""
        if self.transport:
            self.transport.close()
            self.transport = None

    @property
    def port(self):
        """Port this server listens on."""
        return self.transport.get_extra_info("socket").getsockname()[1]

    def connection_made(self, transport):
        """Handle that connection succeeded."""
        self.transport = transport

    def datagram_received(self, data, addr):
        """Handle incoming data."""
        # _LOGGER.debug("Received audio packet: %s", data)

    def error_received(self, exc) -> None:
        """Handle a connection error."""
        self.transport.close()
        _LOGGER.error("Audio receive error: %s", exc)

    def connection_lost(self, exc):
        """Handle that connection was lost."""
        _LOGGER.debug("Audio receiver lost connection (%s)", exc)


class TimingServer(asyncio.Protocol):
    """Protocol used for time synchronization."""

    def __init__(self):
        """Initialize a new TimingServer instance."""
        self.transport = None

    def close(self):
        """Close timing server."""
        if self.transport:
            self.transport.close()
            self.transport = None

    @property
    def port(self):
        """Port this server listens on."""
        return self.transport.get_extra_info("socket").getsockname()[1]

    def connection_made(self, transport):
        """Handle that connection succeeded."""
        self.transport = transport

    def datagram_received(self, data, addr):
        """Handle incoming data."""
        _LOGGER.debug("Received timing packet: %s", data)

    def error_received(self, exc) -> None:
        """Handle a connection error."""
        self.transport.close()
        _LOGGER.error("Timing receive error: %s", exc)

    def connection_lost(self, exc):
        """Handle that connection was lost."""
        _LOGGER.debug("Timing server lost connection (%s)", exc)


class ControlServer(asyncio.Protocol):
    """Protocol used for control channel."""

    def __init__(self):
        """Initialize a new ControlServer instance."""
        self.transport = None

    def close(self):
        """Close control channel."""
        if self.transport:
            self.transport.close()
            self.transport = None

    @property
    def port(self):
        """Port this server listens on."""
        return self.transport.get_extra_info("socket").getsockname()[1]

    def connection_made(self, transport):
        """Handle that connection succeeded."""
        self.transport = transport

    def datagram_received(self, data, addr):
        """Handle incoming data."""
        _LOGGER.debug("Received control packet: %s", data)

    def error_received(self, exc) -> None:
        """Handle a connection error."""
        self.transport.close()
        _LOGGER.error("Control channel receive error: %s", exc)

    def connection_lost(self, exc):
        """Handle that connection was lost."""
        _LOGGER.debug("Control channel lost connection (%s)", exc)


class FakeRaopState:
    """Internal state for RAOP service."""

    def __init__(self):
        pass


class FakeRaopService(HttpSimpleRouter):
    """Implementation of a fake RAOP device."""

    def __init__(self, state, app, loop):
        """Initialize a new FakeRaopService instance."""
        super().__init__()
        self.loop: asyncio.AbstractEventLoop = loop
        self.state: FakeRaopState = state
        self.server: Optional[BasicHttpServer] = None
        self.port: int = None
        self._audio_receiver: Optional[AudioReceiver] = None
        self._timing_server: Optional[TimingServer] = None
        self._control_server: Optional[ControlServer] = None
        self.add_route("ANNOUNCE", "rtsp://.*", self.handle_announce)
        self.add_route("SETUP", "rtsp://*", self.handle_setup)
        self.add_route("SET_PARAMETER", "rtsp://*", self.handle_set_parameter)
        self.add_route("POST", "/feedback", self.handle_feedback)
        self.add_route("RECORD", "rtsp://*", self.handle_record)

    async def start(self, start_web_server: bool):
        self.server, self.port = await http_server(lambda: BasicHttpServer(self))

        local_addr = ("127.0.0.1", 0)
        (_, audio_receiver) = await self.loop.create_datagram_endpoint(
            AudioReceiver,
            local_addr=local_addr,
        )
        (_, timing_server) = await self.loop.create_datagram_endpoint(
            TimingServer,
            local_addr=local_addr,
        )
        (_, control_server) = await self.loop.create_datagram_endpoint(
            ControlServer,
            local_addr=local_addr,
        )

        self._audio_receiver = cast(AudioReceiver, audio_receiver)
        self._timing_server = cast(TimingServer, timing_server)
        self._control_server = cast(TimingServer, control_server)
        _LOGGER.debug(
            "Started RAOP server: port=%d, audio=%d, timing=%d, control=%d",
            self.port,
            self._audio_receiver.port,
            self._timing_server.port,
            self._control_server.port,
        )

    async def cleanup(self):
        if self.server:
            self.server.close()
        if self._audio_receiver:
            self._audio_receiver.close()
        if self._timing_server:
            self._timing_server.close()
        if self._control_server:
            self._control_server.close()

    def handle_announce(self, request: HttpRequest) -> Optional[HttpResponse]:
        """Handle incoming ANNOUNCE request."""
        _LOGGER.debug("Received ANNOUNCE: %s", request)
        return HttpResponse(
            "RTSP", "1.0", 200, "OK", {"CSeq": request.headers["CSeq"]}, b""
        )

    def handle_setup(self, request: HttpRequest) -> Optional[HttpResponse]:
        """Handle incoming SETUP request."""
        _LOGGER.debug("Received SETUP: %s", request)
        headers = {
            "Transport": (
                "RTP/AVP/UDP;unicast;mode=record;"
                f"server_port={self._audio_receiver.port};"
                f"control_port={self._control_server.port};"
                f"timing_port={self._timing_server.port}"
            ),
            "Session": "1",
            "CSeq": request.headers["CSeq"],
        }
        return HttpResponse("RTSP", "1.0", 200, "OK", headers, b"")

    def handle_set_parameter(self, request: HttpRequest) -> Optional[HttpResponse]:
        """Handle incoming SET_PARAMETER request."""
        _LOGGER.debug("Received SET_PARAMETER: %s", request)
        return HttpResponse(
            "RTSP", "1.0", 200, "OK", {"CSeq": request.headers["CSeq"]}, b""
        )

    def handle_feedback(self, request: HttpRequest) -> Optional[HttpResponse]:
        """Handle incoming feedback request."""
        _LOGGER.debug("Received feedback: %s", request)
        return HttpResponse(
            "RTSP", "1.0", 200, "OK", {"CSeq": request.headers["CSeq"]}, b""
        )

    def handle_record(self, request: HttpRequest) -> Optional[HttpResponse]:
        """Handle incoming RECORD request."""
        _LOGGER.debug("Received RECORD: %s", request)
        return HttpResponse(
            "RTSP", "1.0", 200, "OK", {"CSeq": request.headers["CSeq"]}, b""
        )


class FakeRaopUseCases:
    """Wrapper for altering behavior of a FakeRaopService instance."""

    def __init__(self, state):
        """Initialize a new FakeRaopUseCases instance."""
        self.state = state
