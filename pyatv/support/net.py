"""Various network utility helpers."""

from contextlib import suppress
from ipaddress import IPv4Address, IPv4Interface
import logging
import platform
import socket
import struct
from typing import List, Optional

from ifaddr import get_adapters

from pyatv import exceptions

_LOGGER = logging.getLogger(__name__)


def unused_port() -> int:
    """Return a port that is unused on the current host."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def mcast_socket(address: Optional[str], port: int = 0) -> socket.socket:
    """Create a multicast capable socket."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, struct.pack("b", 10))
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, True)

    if hasattr(socket, "SO_REUSEPORT"):
        # FIXME: On windows, SO_REUSEPORT is not available and pylint is still not able
        # to detect that it has been checked with hasattr above:
        # https://github.com/PyCQA/pylint/issues/801
        sock.setsockopt(
            socket.SOL_SOCKET, socket.SO_REUSEPORT, 1  # pylint: disable=no-member
        )

    if address is not None:
        with suppress(OSError):
            sock.setsockopt(
                socket.SOL_IP, socket.IP_MULTICAST_IF, socket.inet_aton(address)
            )

        with suppress(OSError):
            membership = socket.inet_aton("224.0.0.251") + socket.inet_aton(address)
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, membership)

    _LOGGER.debug("Binding on %s:%d", address or "*", port)
    sock.bind((address or "", port))
    return sock


def get_local_address_reaching(dest_ip: IPv4Address) -> Optional[IPv4Address]:
    """Get address of a local interface within same subnet as provided address."""
    for adapter in get_adapters():
        for addr in [addr for addr in adapter.ips if addr.is_IPv4]:
            iface = IPv4Interface(f"{addr.ip}/{addr.network_prefix}")
            if dest_ip in iface.network:
                return iface.ip
    return None


def get_private_addresses(include_loopback=True) -> List[IPv4Address]:
    """Get private (RFC1918 + loopback) addresses from all interfaces."""
    addresses: List[IPv4Address] = []
    for adapter in get_adapters():
        for addr in [addr for addr in adapter.ips if addr.is_IPv4]:
            ipaddr = IPv4Address(addr.ip)
            if ipaddr.is_loopback and not include_loopback:
                continue
            if ipaddr.is_private:
                addresses.append(ipaddr)

    return addresses


# Reference: https://stackoverflow.com/a/14855726
def tcp_keepalive(sock) -> None:
    """Configure keep-alive on a socket."""
    current_platform = platform.system()

    if not hasattr(socket, "SO_KEEPALIVE"):
        raise exceptions.NotSupportedError("System does not support keep-alive")

    sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)

    # Default values are 1s idle time, 5s interval and 4 fails
    keepalive_options = {
        "TCP_KEEPIDLE": 1,
        "TCP_KEEPINTVL": 5,
        "TCP_KEEPCNT": 4,
    }

    for option_name, value in keepalive_options.items():
        try:
            option = getattr(socket, option_name)
        except AttributeError as ex:
            if current_platform == "Darwin" and option_name == "TCP_KEEPIDLE":
                # TCP_KEEPALIVE will hopefully be available at some point,
                # (https://bugs.python.org/issue34932) but until then the value is
                # hardcoded.
                # https://github.com/apple/darwin-xnu/blob/
                #   0a798f6738bc1db01281fc08ae024145e84df927/bsd/netinet/tcp.h#L206
                option = 0x10
            else:
                raise exceptions.NotSupportedError(
                    f"Option {option_name} is not supported"
                ) from ex
        try:
            sock.setsockopt(socket.IPPROTO_TCP, option, value)
        except OSError as ex:
            # Warn here instead of raising exception (we just try to do our best)
            _LOGGER.warning(
                "Unable to set %s (0x%x) on %s: %s", option_name, option, sock, ex
            )

    _LOGGER.debug("Configured keep-alive on %s (%s)", sock, current_platform)
