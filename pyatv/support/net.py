"""Methods used to make GET/POST requests."""

import socket
import logging
from ipaddress import IPv4Interface, IPv4Address
from typing import Optional

import netifaces
from aiohttp import ClientSession

from pyatv.support import log_binary

_LOGGER = logging.getLogger(__name__)


# This timeout is rather long and that is for a reason. If a device is sleeping, it
# automatically wakes up when a service is requested from it. Up to 20 seconds or so
# have been seen. So to deal with that, keep this high.
DEFAULT_TIMEOUT = 25.0  # Seconds


def is_custom_session(session):
    """Return if a ClientSession was created by pyatv."""
    return hasattr(session, "_pyatv")


async def create_session(loop):
    """Create aiohttp ClientSession manged by pyatv."""
    session = ClientSession(loop=loop)
    setattr(session, "_pyatv", True)
    return session


def unused_port() -> int:
    """Return a port that is unused on the current host."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def get_local_address_reaching(dest_ip: IPv4Address) -> Optional[IPv4Address]:
    """Get address of a local interface within same subnet as provided address."""
    for iface in netifaces.interfaces():
        for addr in netifaces.ifaddresses(iface).get(netifaces.AF_INET, []):
            iface = IPv4Interface(addr["addr"] + "/" + addr["netmask"])
            if dest_ip in iface.network:
                return iface.ip
    return None


class HttpSession:
    """This class simplifies GET/POST requests."""

    def __init__(self, client_session, base_url):
        """Initialize a new HttpSession."""
        self._session = client_session  # aiohttp session
        self.base_url = base_url

    async def get_data(self, path, headers=None, timeout=None):
        """Perform a GET request."""
        url = self.base_url + path
        _LOGGER.debug("GET URL: %s", url)
        resp = None
        try:
            resp = await self._session.get(
                url,
                headers=headers,
                timeout=DEFAULT_TIMEOUT if timeout is None else timeout,
            )
            _LOGGER.debug(
                "Response: status=%d, headers=[%s]",
                resp.status,
                ", ".join([f"{key}={value}" for key, value in resp.headers.items()]),
            )
            if resp.content_length is not None:
                resp_data = await resp.read()
                log_binary(_LOGGER, "<< GET", Data=resp_data)
            else:
                resp_data = None
            return resp_data, resp.status
        except Exception as ex:
            if resp is not None:
                resp.close()
            raise ex
        finally:
            if resp is not None:
                await resp.release()

    async def post_data(self, path, data=None, headers=None, timeout=None):
        """Perform a POST request."""
        url = self.base_url + path
        _LOGGER.debug("POST URL: %s", url)
        log_binary(_LOGGER, ">> POST", Data=data)

        resp = None
        try:
            resp = await self._session.post(
                url,
                headers=headers,
                data=data,
                timeout=DEFAULT_TIMEOUT if timeout is None else timeout,
            )
            _LOGGER.debug(
                "Response: status=%d, headers=[%s]",
                resp.status,
                ", ".join([f"{key}={value}" for key, value in resp.headers.items()]),
            )
            if resp.content_length is not None:
                resp_data = await resp.read()
            else:
                resp_data = None
                log_binary(_LOGGER, "<< POST", Data=resp_data)
            return resp_data, resp.status
        except Exception as ex:
            if resp is not None:
                resp.close()
            raise ex
        finally:
            if resp is not None:
                await resp.release()
