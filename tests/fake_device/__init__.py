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
    def __init__(self, loop) -> None:
        self.services = {}  # Protocol > (service, state, usecase)
        self.app = web.Application()
        self.loop = loop
        self.app.on_startup.append(self._app_start)
        self._has_started = False

    async def _app_start(self, _):
        await self.start()

    async def start(self) -> None:
        if self._has_started:
            return

        for service in self.services.values():
            await service[0].start()

        self._has_started = True

    def add_service(self, protocol: Protocol, **kwargs):
        service_factory, state_factory, usecase_factory = FACTORIES.get(protocol)

        state = state_factory(**kwargs)
        service = service_factory(state, self.app, self.loop)
        usecase = usecase_factory(state)
        self.services[protocol] = (service, state, usecase)
        return state, usecase

    # Disclaimer: The implementation is adapted to work with unit tests for now. Since
    # both AirPlay and DMAP depends on the test case to set up a web server, serving
    # each service, it is only the test case that knows about the port. This should be
    # changed in the future to not depend on running in a test environment, but this is
    # a first step.
    def get_port(self, protocol: Protocol) -> int:
        if protocol == Protocol.MRP:
            return self.services[protocol][0].port
        raise Exception("not supported for protocol: " + protocol.name)
