"""Main routines for interacting with an Apple TV."""

import asyncio
import datetime  # noqa
from ipaddress import IPv4Address
import logging
from typing import List, Optional, Set, Union

import aiohttp

from pyatv import conf, exceptions, interface
from pyatv.const import Protocol
from pyatv.core.facade import FacadeAppleTV
from pyatv.protocols import PROTOCOLS
from pyatv.support import http
from pyatv.support.scan import BaseScanner, MulticastMdnsScanner, UnicastMdnsScanner

_LOGGER = logging.getLogger(__name__)


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

    for proto, proto_impl in PROTOCOLS.items():
        # If specific protocols was given, skip this one if it isn't listed
        if protocol and proto not in protocols:
            continue

        for service_type, handler in proto_impl.scan().items():
            scanner.add_service(service_type, handler, proto_impl.device_info)

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
            proto_impl = PROTOCOLS.get(service.protocol)
            if not proto_impl:
                raise RuntimeError(
                    f"missing implementation for protocol {service.protocol}"
                )

            for setup_data in proto_impl.setup(
                loop, config, service, atv, session_manager
            ):
                atv.add_protocol(setup_data)

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

    proto_impl = PROTOCOLS.get(protocol)
    if not proto_impl:
        raise RuntimeError(f"missing implementation for {protocol}")

    session = await http.create_session(session)
    try:
        return proto_impl.pair(config, service, session, loop, **kwargs)
    except Exception:
        await session.close()
        raise
