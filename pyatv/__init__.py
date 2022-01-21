"""Main routines for interacting with an Apple TV."""

import asyncio
from copy import deepcopy
import datetime  # noqa
from functools import partial
from ipaddress import IPv4Address
import logging
from typing import List, Optional, Set, Union

import aiohttp
from zeroconf.asyncio import AsyncZeroconf

from pyatv import exceptions, interface
from pyatv.const import Protocol
from pyatv.core import Core, CoreStateDispatcher, ProtocolStateDispatcher
from pyatv.core.facade import FacadeAppleTV
from pyatv.core.scan import (
    BaseScanner,
    MulticastMdnsScanner,
    UnicastMdnsScanner,
    ZeroconfScanner,
)
from pyatv.protocols import PROTOCOLS
from pyatv.support import http

_LOGGER = logging.getLogger(__name__)


async def scan(
    loop: asyncio.AbstractEventLoop,
    timeout: int = 5,
    identifier: Optional[Union[str, Set[str]]] = None,
    protocol: Optional[Union[Protocol, Set[Protocol]]] = None,
    hosts: List[str] = None,
    aiozc: Optional[AsyncZeroconf] = None,
) -> List[interface.BaseConfig]:
    """Scan for Apple TVs on network and return their configurations.

    When passing in an aiozc instance, a ServiceBrowser must
    be running for all the types in the protocols that being scanned for.
    """

    def _should_include(atv):
        if not atv.ready:
            return False

        if identifier:
            target = identifier if isinstance(identifier, set) else {identifier}
            return not target.isdisjoint(atv.all_identifiers)

        return True

    scanner: BaseScanner
    if aiozc:
        if hosts:
            scanner = ZeroconfScanner(
                aiozc, hosts=[IPv4Address(host) for host in hosts]
            )
        else:
            scanner = ZeroconfScanner(aiozc)
    else:
        if hosts:
            scanner = UnicastMdnsScanner([IPv4Address(host) for host in hosts], loop)
        else:
            scanner = MulticastMdnsScanner(loop, identifier)

    protocols = set()
    if protocol:
        protocols.update(protocol if isinstance(protocol, set) else {protocol})

    for proto, proto_methods in PROTOCOLS.items():
        # If specific protocols was given, skip this one if it isn't listed
        if protocol and proto not in protocols:
            continue

        scanner.add_service_info(proto, proto_methods.service_info)

        for service_type, handler in proto_methods.scan().items():
            scanner.add_service(
                service_type,
                handler,
                proto_methods.device_info,
            )

    devices = (await scanner.discover(timeout)).values()
    return [device for device in devices if _should_include(device)]


async def connect(
    config: interface.BaseConfig,
    loop: asyncio.AbstractEventLoop,
    protocol: Protocol = None,
    session: aiohttp.ClientSession = None,
) -> interface.AppleTV:
    """Connect to a device based on a configuration."""
    if not config.services:
        raise exceptions.NoServiceError("no service to connect to")

    if config.identifier is None:
        raise exceptions.DeviceIdMissingError("no device identifier")

    config_copy = deepcopy(config)
    session_manager = await http.create_session(session)
    core_dispatcher = CoreStateDispatcher()
    atv = FacadeAppleTV(config_copy, session_manager, core_dispatcher)

    try:
        for proto, proto_methods in PROTOCOLS.items():
            service = config_copy.get_service(proto)
            if service is None or not service.enabled:
                continue
            if not service.enabled:
                _LOGGER.debug("Ignore %s as it is disabled", proto.name)
                continue

            # Lock protocol argument so protocol does not have to deal
            # with that
            takeover_method = partial(atv.takeover, proto)

            # Core provides core access with a protocol specific twist
            core = Core(
                loop,
                config_copy,
                service,
                atv,
                session_manager,
                takeover_method,
                ProtocolStateDispatcher(proto, core_dispatcher),
            )

            for setup_data in proto_methods.setup(core):
                atv.add_protocol(setup_data)

        await atv.connect()
    except Exception:
        await session_manager.close()
        raise
    else:
        return atv


async def pair(
    config: interface.BaseConfig,
    protocol: Protocol,
    loop: asyncio.AbstractEventLoop,
    session: aiohttp.ClientSession = None,
    **kwargs
):
    """Pair a protocol for an Apple TV."""
    service = config.get_service(protocol)
    if not service:
        raise exceptions.NoServiceError(f"no service available for {protocol}")

    proto_methods = PROTOCOLS.get(protocol)
    if not proto_methods:
        raise RuntimeError(f"missing implementation for {protocol}")

    session = await http.create_session(session)
    try:
        return proto_methods.pair(config, service, session, loop, **kwargs)
    except Exception:
        await session.close()
        raise
