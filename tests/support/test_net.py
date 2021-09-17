"""Unit tests for pyatv.support.net."""

from ipaddress import IPv4Address, ip_address
import platform
import socket
import sys
from typing import Dict, List
from unittest.mock import patch

import netifaces
import pytest

from pyatv.exceptions import NotSupportedError
from pyatv.support.net import get_private_addresses, tcp_keepalive

skip_darwin = pytest.mark.skipif(
    platform.system() == "Darwin",
    reason="not applicable to Darwin",
)


def skip_before_win_build(build_number: int):
    """Mark a test to be skipped if Windows is earlier than the given build."""
    system = platform.system()
    version = platform.version()
    return pytest.mark.skipif(
        (
            system == "Windows"
            and tuple(map(int, version.split("."))) < (10, 0, build_number)
        ),
        reason="Windows build number too low",
    )


@pytest.fixture(autouse=True)
def mock_address():
    addresses: Dict[str, List[str]] = {}

    def _add(interface: str, address: IPv4Address):
        addresses.setdefault(interface, []).append(address)

    def _ifaddresses(interface: str):
        iface_addresses = addresses.get(interface)
        if not iface_addresses:
            return {}

        inet_addresses = [
            {"addr": str(addr), "netmask": "255.255.255.0"} for addr in iface_addresses
        ]
        return {netifaces.AF_INET: inet_addresses}

    with patch("netifaces.interfaces") as mock_interfaces:
        with patch("netifaces.ifaddresses") as mock_ifaddr:
            mock_interfaces.side_effect = lambda: list(addresses.keys())
            mock_ifaddr.side_effect = _ifaddresses
            yield _add


@pytest.fixture
def mock_server():
    sock = socket.socket()
    # 127.0.0.1 *must* be used when testing on macOS
    sock.bind(("127.0.0.1", 0))
    sock.listen(1)
    yield sock
    sock.close()


@pytest.fixture
def mock_client(mock_server):
    sock = socket.socket()
    sock.connect(mock_server.getsockname())
    yield sock
    sock.close()


def test_no_address():
    assert get_private_addresses() == []


def test_private_addresses(mock_address):
    mock_address("wlan0", "10.0.0.1")
    mock_address("eth0", "192.168.0.1")
    mock_address("eth1", "172.16.0.1")

    assert get_private_addresses() == [
        ip_address("10.0.0.1"),
        ip_address("192.168.0.1"),
        ip_address("172.16.0.1"),
    ]


def test_public_addresses(mock_address):
    mock_address("eth0", "1.2.3.4")
    mock_address("eth1", "8.8.8.8")
    assert get_private_addresses() == []


def test_localhost(mock_address):
    mock_address("eth0", "127.0.0.1")
    assert get_private_addresses() == [IPv4Address("127.0.0.1")]


# Windows 10 1709 (build 16299) is the first version with TCP_KEEPIDLE
# ref: https://github.com/python/cpython/blob/66d3b589c44fcbcf9afe1e442d9beac3bd8bcd34/Modules/socketmodule.c#L318-L322 # noqa
@skip_before_win_build(16299)
# More specifically, TCP_KEEPIDLE and TCP_KEEPINTVL were added in 3.7, while 3.6.5 added
# TCP_KEEPCNT
# ref: `socket.SO_*` documentation.
@pytest.mark.skipif(sys.version_info < (3, 7), reason="keepalive added in 3.7")
def test_keepalive(mock_server, mock_client):
    """Test that TCP keepalive can be enabled."""
    server2client, client_address = mock_server.accept()
    with server2client:
        # No assert, as we're just testing that enabling keepalive works
        tcp_keepalive(mock_client)


# TCP keepalive options to remove one at a time
TCP_KEEPALIVE_OPTIONS = [
    # Darwin has a hard-coded value for the equivalent option
    pytest.param("TCP_KEEPIDLE", marks=skip_darwin),
    "TCP_KEEPINTVL",
    "TCP_KEEPCNT",
]


@pytest.mark.parametrize("missing_option", TCP_KEEPALIVE_OPTIONS)
def test_keepalive_missing_sockopt(
    missing_option,
    mock_server,
    mock_client,
    monkeypatch,
):
    """Test that missing keepalive options raise `NotSupportedError`."""
    # If the option is already missing, don't raise an error (raising=False)
    monkeypatch.delattr(socket, missing_option, raising=False)
    server2client, client_address = mock_server.accept()
    with server2client:
        with pytest.raises(NotSupportedError):
            tcp_keepalive(mock_client)
