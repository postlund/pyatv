from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
import netifaces

from pyatv.support.net import unused_port

from tests.fake_knock import create_knock_server
from tests.utils import stub_sleep, unstub_sleep


@pytest.fixture(autouse=True)
def stub_netifaces():
    methods = {
        "interfaces": Mock(return_value=["eth0"]),
        "ifaddresses": Mock(
            return_value={
                netifaces.AF_INET: [
                    {
                        "addr": "10.0.10.1",
                        "netmask": "255.255.255.0",
                        "broadcast": "10.0.10.255",
                    },
                    {
                        "addr": "127.0.0.1",
                        "netmask": "255.0.0.0",
                    },
                ]
            }
        ),
    }

    with patch.multiple("netifaces", **methods):
        yield


@pytest.fixture(autouse=True, name="stub_sleep")
def stub_sleep_fixture():
    stub_sleep()
    yield
    unstub_sleep()


@pytest.fixture
async def knock_server(event_loop):
    servers = []

    async def _add_server():
        server, knock_server = await create_knock_server(unused_port(), event_loop)
        servers.append(server)
        return knock_server

    yield _add_server

    for server in servers:
        server.close()


@pytest.fixture
def stub_knock_server():
    with patch("pyatv.support.knock.knock") as knock:
        info = SimpleNamespace(ports=set(), knock_count=0)

        async def _stub_knock(address, ports, loop):
            info.ports.update(ports)
            info.knock_count += 1

        knock.side_effect = _stub_knock
        yield info
