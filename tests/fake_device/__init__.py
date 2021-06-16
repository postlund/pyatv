"""Representation of a fake device supporting multiple protocol."""
from collections import namedtuple
from typing import Dict

from aiohttp import web

from pyatv.const import Protocol

from tests.fake_device.airplay import (
    FakeAirPlayService,
    FakeAirPlayState,
    FakeAirPlayUseCases,
)
from tests.fake_device.companion import (
    FakeCompanionServiceFactory,
    FakeCompanionState,
    FakeCompanionUseCases,
)
from tests.fake_device.dmap import FakeDmapService, FakeDmapState, FakeDmapUseCases
from tests.fake_device.mrp import FakeMrpServiceFactory, FakeMrpState, FakeMrpUseCases
from tests.fake_device.raop import FakeRaopService, FakeRaopState, FakeRaopUseCases

FACTORIES = {
    Protocol.AirPlay: (FakeAirPlayService, FakeAirPlayState, FakeAirPlayUseCases),
    Protocol.DMAP: (FakeDmapService, FakeDmapState, FakeDmapUseCases),
    Protocol.MRP: (FakeMrpServiceFactory, FakeMrpState, FakeMrpUseCases),
    Protocol.Companion: (
        FakeCompanionServiceFactory,
        FakeCompanionState,
        FakeCompanionUseCases,
    ),
    Protocol.RAOP: (FakeRaopService, FakeRaopState, FakeRaopUseCases),
}

FakeService = namedtuple("FakeService", "service state usecase")


class FakeAppleTV:
    def __init__(self, loop, test_mode=True) -> None:
        self.services: Dict[Protocol, FakeService] = {}
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
            await service.service.start(not self.test_mode)

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
        self.services[protocol] = FakeService(service, state, usecase)
        return state, usecase

    # Disclaimer: When running in "test mode", only MRP and Companion is supported here!
    def get_port(self, protocol: Protocol) -> int:
        return self.services[protocol].service.port

    def get_state(self, protocol: Protocol):
        return self.services[protocol].state

    def get_usecase(self, protocol: Protocol):
        return self.services[protocol].usecase
