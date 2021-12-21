"""Module used for pairing pyatv with a device."""

import asyncio
import hashlib
from io import StringIO
from ipaddress import IPv4Address
import logging
import random
from typing import List, Optional

from aiohttp import web
from zeroconf import Zeroconf

from pyatv import exceptions
from pyatv.core import AbstractPairingHandler, mdns
from pyatv.interface import BaseConfig, BaseService
from pyatv.protocols.dmap import tags
from pyatv.support.http import ClientSessionManager
from pyatv.support.net import get_private_addresses, unused_port

_LOGGER = logging.getLogger(__name__)


def _get_zeroconf_addresses(addresses: Optional[List[str]]) -> List[IPv4Address]:
    if addresses is None:
        return list(get_private_addresses(include_loopback=False))

    return [IPv4Address(address) for address in addresses]


def _generate_random_guid():
    return hex(random.getrandbits(64)).upper()


class DmapPairingHandler(AbstractPairingHandler):
    """Handle the pairing process.

    This class will publish a bonjour service and configure a webserver
    that responds to pairing requests.
    """

    def __init__(
        self,
        config: BaseConfig,
        service: BaseService,
        session_manager: ClientSessionManager,
        loop: asyncio.AbstractEventLoop,
        **kwargs
    ) -> None:
        """Initialize a new instance."""
        super().__init__(session_manager, service, device_provides_pin=False)
        self._loop = loop
        self._zeroconf: Zeroconf = kwargs.get("zeroconf") or Zeroconf()
        self._name: str = kwargs.get("name", "pyatv")
        self.app = web.Application()
        self.app.router.add_routes([web.get("/pair", self.handle_request)])
        self.runner: web.AppRunner = web.AppRunner(self.app)
        self._got_valid_response: bool = False
        self._pairing_guid: str = (
            kwargs.get("pairing_guid") or _generate_random_guid()
        )[2:].upper()
        self._addresses: List[IPv4Address] = _get_zeroconf_addresses(
            kwargs.get("addresses")
        )

    async def close(self) -> None:
        """Call to free allocated resources after pairing."""
        self._zeroconf.close()
        await self.runner.cleanup()
        await super().close()

    async def _pair_begin(self) -> None:
        """Start the pairing server and publish service."""
        port = unused_port()

        await self.runner.setup()
        site = web.TCPSite(self.runner, "0.0.0.0", port)
        await site.start()

        _LOGGER.debug("Started pairing web server at port %d", port)

        for ipaddr in self._addresses:
            await self._publish_service(ipaddr, port)

    async def _pair_finish(self) -> str:
        """Stop pairing server and unpublish service."""
        if self._got_valid_response:
            return f"0x{self._pairing_guid}"
        raise exceptions.PairingError("pairing failed")

    async def _publish_service(self, address: IPv4Address, port: int) -> None:
        props = {
            "DvNm": self._name,
            "RemV": "10000",
            "DvTy": "iPod",
            "RemN": "Remote",
            "txtvers": "1",
            "Pair": self._pairing_guid,
        }

        await mdns.publish(
            self._loop,
            mdns.Service(
                "_touch-remote._tcp.local",
                f"{int(address):040d}",
                address,
                port,
                props,
            ),
            self._zeroconf,
        )

    async def handle_request(self, request) -> None:
        """Respond to request if PIN is correct."""
        service_name = request.rel_url.query["servicename"]
        received_code = request.rel_url.query["pairingcode"].lower()
        _LOGGER.info(
            "Got pairing request from %s with code %s", service_name, received_code
        )

        if self._verify_pin(received_code):
            cmpg = tags.uint64_tag("cmpg", int(self._pairing_guid, 16))
            cmnm = tags.string_tag("cmnm", self._name)
            cmty = tags.string_tag("cmty", "iPhone")
            response = tags.container_tag("cmpa", cmpg + cmnm + cmty)
            self._got_valid_response = True
            return web.Response(body=response)

        # Code did not match, generate an error
        return web.Response(status=500)

    def _verify_pin(self, received_code: str) -> bool:
        merged = StringIO()
        merged.write(self._pairing_guid)
        for char in str(self._pin or 0).zfill(4):
            merged.write(char)
            merged.write("\x00")

        expected_code = hashlib.md5(merged.getvalue().encode()).hexdigest()
        _LOGGER.debug("Got code %s, expects %s", received_code, expected_code)
        return received_code == expected_code
