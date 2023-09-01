"""Module used for pairing pyatv with a device."""

import hashlib
from io import StringIO
from ipaddress import IPv4Address
import logging
import random
from typing import List, Optional

from aiohttp import web
from zeroconf import Zeroconf

from pyatv.core import Core, mdns
from pyatv.interface import PairingHandler
from pyatv.protocols.dmap import tags
from pyatv.support.net import get_private_addresses, unused_port

_LOGGER = logging.getLogger(__name__)


def _get_zeroconf_addresses(addresses: Optional[List[str]]) -> List[IPv4Address]:
    if addresses is None:
        return list(get_private_addresses(include_loopback=False))

    return [IPv4Address(address) for address in addresses]


def _generate_random_guid():
    return hex(random.getrandbits(64)).upper()


class DmapPairingHandler(
    PairingHandler
):  # pylint: disable=too-many-instance-attributes  # noqa
    """Handle the pairing process.

    This class will publish a bonjour service and configure a webserver
    that responds to pairing requests.
    """

    def __init__(self, core: Core, **kwargs) -> None:
        """Initialize a new instance."""
        super().__init__(core.session_manager, core.service)
        self._core = core
        self._zeroconf: Zeroconf = kwargs.get("zeroconf") or Zeroconf()
        self._name: str = kwargs.get("name", core.settings.info.name)
        self.app = web.Application()
        self.app.router.add_routes([web.get("/pair", self.handle_request)])
        self.runner: web.AppRunner = web.AppRunner(self.app)
        self.site: Optional[web.TCPSite] = None
        self._pin_code: Optional[int] = None
        self._has_paired: bool = False
        self._pairing_guid: str = (
            kwargs.get("pairing_guid", None) or _generate_random_guid()
        )[2:].upper()
        self._addresses: List[IPv4Address] = _get_zeroconf_addresses(
            kwargs.get("addresses")
        )

    async def close(self) -> None:
        """Call to free allocated resources after pairing."""
        self._zeroconf.close()
        await self.runner.cleanup()
        await super().close()

    @property
    def has_paired(self) -> bool:
        """If a successful pairing has been performed.

        The value will be reset when stop() is called.
        """
        return self._has_paired

    async def begin(self) -> None:
        """Start the pairing server and publish service."""
        port = unused_port()

        await self.runner.setup()
        self.site = web.TCPSite(self.runner, "0.0.0.0", port)
        await self.site.start()

        _LOGGER.debug("Started pairing web server at port %d", port)

        for ipaddr in self._addresses:
            await self._publish_service(ipaddr, port)

    async def finish(self) -> None:
        """Stop pairing server and unpublish service."""
        if self._has_paired:
            _LOGGER.debug("Saving updated credentials")
            self.service.credentials = "0x" + self._pairing_guid
            self._core.settings.protocols.dmap.credentials = self.service.credentials

    def pin(self, pin: int) -> None:
        """Pin code used for pairing."""
        self._pin_code = pin
        _LOGGER.debug("DMAP PIN changed to %s", self._pin_code)

    @property
    def device_provides_pin(self) -> bool:
        """Return True if remote device presents PIN code, else False."""
        return False

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
            self._core.loop,
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
            self._has_paired = True
            return web.Response(body=response)

        # Code did not match, generate an error
        return web.Response(status=500)

    def _verify_pin(self, received_code: str) -> bool:
        # If no particular pin code is specified, allow any pin
        if self._pin_code is None:
            return True

        merged = StringIO()
        merged.write(self._pairing_guid)
        for char in str(self._pin_code).zfill(4):
            merged.write(char)
            merged.write("\x00")

        expected_code = hashlib.md5(merged.getvalue().encode()).hexdigest()
        _LOGGER.debug("Got code %s, expects %s", received_code, expected_code)
        return received_code == expected_code
