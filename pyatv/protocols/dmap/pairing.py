"""Module used for pairing pyatv with a device."""

import asyncio
import hashlib
from io import StringIO
import ipaddress
import logging
import random

from aiohttp import web
import netifaces
from zeroconf import Zeroconf

from pyatv.core import mdns
from pyatv.interface import BaseConfig, BaseService, PairingHandler
from pyatv.protocols.dmap import tags
from pyatv.support.http import ClientSessionManager
from pyatv.support.net import unused_port

_LOGGER = logging.getLogger(__name__)


# Maybe replace with pyatv.net.get_local_address_reaching?
def _get_private_ip_addresses():
    for iface in netifaces.interfaces():
        addresses = netifaces.ifaddresses(iface)
        if netifaces.AF_INET not in addresses:
            continue

        for addr in addresses[netifaces.AF_INET]:
            ipaddr = ipaddress.ip_address(addr["addr"])
            if ipaddr.is_private and not ipaddr.is_loopback:
                yield ipaddr


def _generate_random_guid():
    return hex(random.getrandbits(64)).upper()


class DmapPairingHandler(
    PairingHandler
):  # pylint: disable=too-many-instance-attributes  # noqa
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
    ):
        """Initialize a new instance."""
        super().__init__(session_manager, service)
        self._loop = loop
        self._zeroconf = kwargs.get("zeroconf") or Zeroconf()
        self._name = kwargs.get("name", "pyatv")
        self.app = web.Application()
        self.app.router.add_routes([web.get("/pair", self.handle_request)])
        self.runner = web.AppRunner(self.app)
        self.site = None
        self._pin_code = None
        self._has_paired = False
        self._pairing_guid = (
            kwargs.get("pairing_guid", None) or _generate_random_guid()
        )[2:].upper()

    async def close(self):
        """Call to free allocated resources after pairing."""
        self._zeroconf.close()
        await self.runner.cleanup()
        await super().close()

    @property
    def has_paired(self):
        """If a successful pairing has been performed.

        The value will be reset when stop() is called.
        """
        return self._has_paired

    async def begin(self):
        """Start the pairing server and publish service."""
        port = unused_port()

        await self.runner.setup()
        self.site = web.TCPSite(self.runner, "0.0.0.0", port)
        await self.site.start()

        _LOGGER.debug("Started pairing web server at port %d", port)

        for ipaddr in _get_private_ip_addresses():
            await self._publish_service(ipaddr, port)

    async def finish(self):
        """Stop pairing server and unpublish service."""
        if self._has_paired:
            _LOGGER.debug("Saving updated credentials")
            self.service.credentials = "0x" + self._pairing_guid

    def pin(self, pin):
        """Pin code used for pairing."""
        self._pin_code = pin
        _LOGGER.debug("DMAP PIN changed to %s", self._pin_code)

    @property
    def device_provides_pin(self):
        """Return True if remote device presents PIN code, else False."""
        return False

    async def _publish_service(self, address, port):
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

    async def handle_request(self, request):
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

    def _verify_pin(self, received_code):
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
