"""Unit tests for the net support module."""

from typing import Dict, List
from ipaddress import IPv4Address, ip_address
from unittest.mock import patch

import pytest
import netifaces

from pyatv.support.net import get_private_addresses


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
