"""Representation of a fake device supporting multiple protocol."""

from aiohttp import web

from pyatv.const import Protocol

from tests.fake_device.airplay import (
    FakeAirPlayService,
    FakeAirPlayUseCases,
    FakeAirPlayState,
)
from tests.fake_device.dmap import FakeDmapService, FakeDmapUseCases, FakeDmapState
from tests.fake_device.mrp import FakeMrpServiceFactory, FakeMrpUseCases, FakeMrpState


FACTORIES = {
    Protocol.AirPlay: (FakeAirPlayService, FakeAirPlayState, FakeAirPlayUseCases),
    Protocol.DMAP: (FakeDmapService, FakeDmapState, FakeDmapUseCases),
    Protocol.MRP: (FakeMrpServiceFactory, FakeMrpState, FakeMrpUseCases),
}


class FakeAppleTV:
    def __init__(self, loop, test_mode=True) -> None:
        self.services = {}  # Protocol > (service, state, usecase)
        self.app = web.Application() if test_mode else None
        self.loop = loop
        self.test_mode = test_mode
        self._has_started = False
        if test_mode:
            self.app.on_startup.append(self._app_start)

    async def _app_start(self, _):
        await self.start()

    async def start(self) -> None:
        if self._has_started:
            return

        for service in self.services.values():
            await service[0].start(not self.test_mode)

        self._has_started = True

    async def stop(self) -> None:
        for service in self.services.values():
            await service[0].cleanup()

        self._has_started = False

    def add_service(self, protocol: Protocol, **kwargs):
        service_factory, state_factory, usecase_factory = FACTORIES.get(protocol)

        state = state_factory(**kwargs)
        service = service_factory(
            state, self.app if self.test_mode else web.Application(), self.loop
        )
        usecase = usecase_factory(state)
        self.services[protocol] = (service, state, usecase)
        return state, usecase

    # Disclaimer: When running in "test mode", only MRP is supported here!
    def get_port(self, protocol: Protocol) -> int:
        return self.services[protocol][0].port
