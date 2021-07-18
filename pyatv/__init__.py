"""Main routines for interacting with an Apple TV."""

import asyncio
import datetime  # noqa
from ipaddress import IPv4Address
import logging
from typing import List, NamedTuple, Optional, Set, Union

import aiohttp

from pyatv import airplay as airplay_proto
from pyatv import companion as companion_proto
from pyatv import conf
from pyatv import dmap as dmap_proto
from pyatv import exceptions, interface
from pyatv import mrp as mrp_proto
from pyatv import raop as raop_proto
from pyatv.airplay.pairing import AirPlayPairingHandler
from pyatv.companion.pairing import CompanionPairingHandler
from pyatv.const import Protocol
from pyatv.dmap.pairing import DmapPairingHandler
from pyatv.mrp.pairing import MrpPairingHandler
from pyatv.support import http
from pyatv.support.facade import FacadeAppleTV, SetupMethod
from pyatv.support.scan import (
    BaseScanner,
    MulticastMdnsScanner,
    ScanMethod,
    UnicastMdnsScanner,
)

_LOGGER = logging.getLogger(__name__)


class ProtocolImpl(NamedTuple):
    """Represent implementation of a protocol."""

    setup: SetupMethod
    scan: ScanMethod


_PROTOCOLS = {
    Protocol.AirPlay: ProtocolImpl(airplay_proto.setup, airplay_proto.scan),
    Protocol.Companion: ProtocolImpl(companion_proto.setup, companion_proto.scan),
    Protocol.DMAP: ProtocolImpl(dmap_proto.setup, dmap_proto.scan),
    Protocol.MRP: ProtocolImpl(mrp_proto.setup, mrp_proto.scan),
    Protocol.RAOP: ProtocolImpl(
        raop_proto.setup,
        raop_proto.scan,
    ),
}


async def scan(
    loop: asyncio.AbstractEventLoop,
    timeout: int = 5,
    identifier: str = None,
    protocol: Optional[Union[Protocol, Set[Protocol]]] = None,
    hosts: List[str] = None,
) -> List[conf.AppleTV]:
    """Scan for Apple TVs on network and return their configurations."""

    def _should_include(atv):
        if not atv.ready:
            return False

        if identifier and identifier not in atv.all_identifiers:
            return False

        return True

    scanner: BaseScanner
    if hosts:
        scanner = UnicastMdnsScanner([IPv4Address(host) for host in hosts], loop)
    else:
        scanner = MulticastMdnsScanner(loop, identifier)

    protocols = set()
    if protocol:
        protocols.update(protocol if isinstance(protocol, set) else {protocol})

    for proto, proto_impl in _PROTOCOLS.items():
        # If specific protocols was given, skip this one if it isn't listed
        if protocol and proto not in protocols:
            continue

        for service_type, handler in proto_impl.scan().items():
            scanner.add_service(service_type, handler)

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

    try:
        for service in config.services:
            proto_impl = _PROTOCOLS.get(service.protocol)
            if not proto_impl:
                raise RuntimeError(
                    "missing implementation for protocol {service.protocol}"
                )

            setup_data = proto_impl.setup(
                loop, config, atv.interfaces, atv, session_manager
            )
            if setup_data:
                _LOGGER.debug("Adding protocol %s", service.protocol)
                atv.add_protocol(service.protocol, setup_data)
            else:
                _LOGGER.debug("Not adding protocol: %s", service.protocol)

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
