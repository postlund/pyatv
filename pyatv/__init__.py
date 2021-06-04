"""Main routines for interacting with an Apple TV."""

import asyncio
import datetime  # noqa
from ipaddress import IPv4Address
import logging
from typing import Dict, List

import aiohttp

from pyatv import conf, exceptions, interface
from pyatv.airplay import setup as airplay_setup
from pyatv.airplay.pairing import AirPlayPairingHandler
from pyatv.companion import setup as companion_setup
from pyatv.companion.pairing import CompanionPairingHandler
from pyatv.const import Protocol
from pyatv.dmap import setup as dmap_setup
from pyatv.dmap.pairing import DmapPairingHandler
from pyatv.mrp import setup as mrp_setup
from pyatv.mrp.pairing import MrpPairingHandler
from pyatv.raop import setup as raop_setup
from pyatv.support import http
from pyatv.support.facade import FacadeAppleTV, SetupMethod
from pyatv.support.scan import BaseScanner, MulticastMdnsScanner, UnicastMdnsScanner

_LOGGER = logging.getLogger(__name__)

_PROTOCOL_IMPLEMENTATIONS: Dict[Protocol, SetupMethod] = {
    Protocol.MRP: mrp_setup,
    Protocol.DMAP: dmap_setup,
    Protocol.AirPlay: airplay_setup,
    Protocol.Companion: companion_setup,
    Protocol.RAOP: raop_setup,
}


async def scan(
    loop: asyncio.AbstractEventLoop,
    timeout: int = 5,
    identifier: str = None,
    protocol: Protocol = None,
    hosts: List[str] = None,
) -> List[conf.AppleTV]:
    """Scan for Apple TVs on network and return their configurations."""

    def _should_include(atv):
        if not atv.ready:
            return False

        if identifier and identifier not in atv.all_identifiers:
            return False

        if protocol and atv.get_service(protocol) is None:
            return False

        return True

    scanner: BaseScanner
    if hosts:
        scanner = UnicastMdnsScanner([IPv4Address(host) for host in hosts], loop)
    else:
        scanner = MulticastMdnsScanner(loop, identifier)

    devices = (await scanner.discover(timeout)).values()
    return [device for device in devices if _should_include(device)]


async def connect(
    config: conf.AppleTV,
    loop: asyncio.AbstractEventLoop,
    protocol: Protocol = None,
    session: aiohttp.ClientSession = None,
) -> interface.AppleTV:
    """Connect to a device based on a configuration."""
    if not config.services:
        raise exceptions.NoServiceError("no service to connect to")

    if config.identifier is None:
        raise exceptions.DeviceIdMissingError("no device identifier")

    session_manager = await http.create_session(session)
    atv = FacadeAppleTV(config, session_manager)

    for service in config.services:
        setup_method = _PROTOCOL_IMPLEMENTATIONS.get(service.protocol)
        if not setup_method:
            raise RuntimeError("missing implementation for protocol {service.protocol}")

        setup_data = setup_method(loop, config, atv.interfaces, atv, session_manager)
        if setup_data:
            _LOGGER.debug("Adding protocol %s", service.protocol)
            atv.add_protocol(service.protocol, setup_data)
        else:
            _LOGGER.debug("Not adding protocol: %s", service.protocol)
    try:
        await atv.connect()
    except Exception:
        await session_manager.close()
        raise
    else:
        return atv


async def pair(
    config: conf.AppleTV,
    protocol: Protocol,
    loop: asyncio.AbstractEventLoop,
    session: aiohttp.ClientSession = None,
    **kwargs
):
    """Pair a protocol for an Apple TV."""
    service = config.get_service(protocol)
    if not service:
        raise exceptions.NoServiceError(f"no service available for {protocol}")

    handler = {
        Protocol.DMAP: DmapPairingHandler,
        Protocol.MRP: MrpPairingHandler,
        Protocol.AirPlay: AirPlayPairingHandler,
        Protocol.Companion: CompanionPairingHandler,
    }.get(protocol)

    if handler is None:
        raise RuntimeError(f"missing implementation for {protocol}")

    return handler(config, await http.create_session(session), loop, **kwargs)
