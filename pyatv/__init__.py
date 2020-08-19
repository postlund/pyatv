"""Main routines for interacting with an Apple TV."""

import asyncio
import datetime  # noqa
from ipaddress import IPv4Address
from typing import List

import aiohttp

from pyatv import conf, exceptions, interface
from pyatv.airplay import AirPlayStreamAPI
from pyatv.const import Protocol
from pyatv.dmap import DmapAppleTV
from pyatv.dmap.pairing import DmapPairingHandler
from pyatv.mrp import MrpAppleTV
from pyatv.mrp.pairing import MrpPairingHandler
from pyatv.airplay.pairing import AirPlayPairingHandler
from pyatv.support import net
from pyatv.support.scan import BaseScanner, UnicastMdnsScanner, MulticastMdnsScanner


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
    if config.identifier is None:
        raise exceptions.DeviceIdMissingError("no device identifier")

    service = config.main_service(protocol=protocol)

    implementation = {Protocol.DMAP: DmapAppleTV, Protocol.MRP: MrpAppleTV}.get(
        service.protocol
    )

    if not implementation:
        raise exceptions.UnsupportedProtocolError(str(service.protocol))

    # AirPlay stream API is the same for both DMAP and MRP
    airplay = AirPlayStreamAPI(config, loop)

    atv = implementation(loop, await net.create_session(session), config, airplay)
    await atv.connect()
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
        raise exceptions.NoServiceError(
            "no service available for protocol " + str(protocol)
        )

    handler = {
        Protocol.DMAP: DmapPairingHandler,
        Protocol.MRP: MrpPairingHandler,
        Protocol.AirPlay: AirPlayPairingHandler,
    }.get(protocol)

    if handler is None:
        raise exceptions.UnsupportedProtocolError(str(protocol))

    return handler(config, await net.create_session(session), loop, **kwargs)
