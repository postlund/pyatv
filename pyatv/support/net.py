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


class ClientSessionManager:
    """Manages an aiohttp ClientSession instance."""

    def __init__(self, session: ClientSession, should_close: bool) -> None:
        """Initialize a new ClientSessionManager."""
        self._session = session
        self._should_close = should_close

    @property
    def session(self) -> ClientSession:
        """Return client session."""
        return self._session

    async def close(self) -> None:
        """Close session."""
        if self._should_close:
            await self.session.close()


async def create_session(
    session: Optional[ClientSession] = None,
) -> ClientSessionManager:
    """Create aiohttp ClientSession manged by pyatv."""
    return ClientSessionManager(session or ClientSession(), session is None)


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

    def __init__(self, client_session: ClientSession, base_url: str):
        """Initialize a new HttpSession."""
        self._session = client_session
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
