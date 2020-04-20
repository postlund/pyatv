from unittest.mock import patch

import pytest

from pyatv.support.net import unused_port

from tests.fake_knock import create_knock_server


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
    knocked_ports = set()
    with patch("pyatv.support.knock.knock") as knock:

        async def _stub_knock(address, ports, loop):
            knocked_ports.update(ports)

        knock.side_effect = _stub_knock
        yield knocked_ports
